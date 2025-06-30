from flask import Flask, render_template, request, jsonify
from model import RoTextSimpModel
import logging
import requests
from urllib.parse import urlparse, unquote
import wikipedia
import traceback

try:
    print("Loading text simplification model...")
    model = RoTextSimpModel()
    print("✓ Text simplification model loaded successfully!")
except Exception as e:
    print(f"✗ Failed to load model: {str(e)}")
    print("Full traceback:")
    traceback.print_exc()
    model = None

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

wikipedia.set_lang('ro')

def extract_wikipedia_content(url_or_title):
    """
    Extract content from Wikipedia article
    Accepts either a Wikipedia URL or just the article title
    """
    try:
        # If it's a URL, extract the title
        if url_or_title.startswith('http'):
            parsed_url = urlparse(url_or_title)
            if 'wikipedia.org' not in parsed_url.netloc:
                raise ValueError("Not a Wikipedia URL")
            
            # Extract title from URL path
            path_parts = parsed_url.path.split('/')
            if 'wiki' in path_parts:
                wiki_index = path_parts.index('wiki')
                if wiki_index + 1 < len(path_parts):
                    title = unquote(path_parts[wiki_index + 1])
                else:
                    raise ValueError("Invalid Wikipedia URL format")
            else:
                raise ValueError("Invalid Wikipedia URL format")
        else:
            # Assume it's already a title
            title = url_or_title.strip()
        
        # Use Wikipedia API to get article content
        api_url = "https://ro.wikipedia.org/api/rest_v1/page/summary/" + title
        headers = {
            'User-Agent': 'Romanian Text Simplification (Educational Purpose)'
        }
        
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('type') == 'disambiguation':
            raise ValueError(f"'{title}' is a disambiguation page. Please specify a more specific article.")
        
        # Get the extract (summary)
        extract = data.get('extract', '')
        
        # For full content, we need to use the other API endpoint
        full_api_url = f"https://ro.wikipedia.org/api/rest_v1/page/html/{title}"
        full_response = requests.get(full_api_url, headers=headers, timeout=15)

        try:
            page = wikipedia.page(title)
            full_content = page.content

            return {
                'title': data.get('title', title),
                'summary': extract,
                'full_content': full_content,
                'url': data.get('content_urls', {}).get('desktop', {}).get('page', '')
            }
        except:
            # Fallback to summary only
            return {
                'title': data.get('title', title),
                'summary': extract,
                'full_content': extract,
                'url': data.get('content_urls', {}).get('desktop', {}).get('page', '')
            }
        
        """
        if full_response.status_code == 200:
            # Parse HTML to extract text content
            h = html2text.HTML2Text()
            h.ignore_links = True
            h.ignore_images = True
            h.ignore_emphasis = False
            full_content = h.handle(full_response.text)
            
            # Clean up the content
            full_content = re.sub(r'\n\s*\n', '\n\n', full_content)  # Remove excessive newlines
            full_content = re.sub(r'\[edit\]', '', full_content)      # Remove [edit] markers
            full_content = full_content.strip()
            
            return {
                'title': data.get('title', title),
                'summary': extract,
                'full_content': full_content,
                'url': data.get('content_urls', {}).get('desktop', {}).get('page', '')
            }
        else:
            # Fallback to summary only
            return {
                'title': data.get('title', title),
                'summary': extract,
                'full_content': extract,
                'url': data.get('content_urls', {}).get('desktop', {}).get('page', '')
            }
        """
            
    except requests.RequestException as e:
        raise ValueError(f"Failed to fetch Wikipedia article: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error processing Wikipedia article: {str(e)}")

@app.route('/')
def index():
    #Serve the main page with the text input form
    return render_template('index.html')

@app.route('/simplify', methods=['POST'])
def simplify_text():
    #Handle text simplification requests
    try:
        # Get text from form
        input_text = request.form.get('text', '').strip()
        
        if not input_text:
            return jsonify({
                'success': False,
                'error': 'Please provide text to simplify'
            }), 400
        
        if len(input_text) > 10000:  # Adjust limit as needed
            return jsonify({
                'success': False,
                'error': 'Text is too long. Please limit to 10,000 characters.'
            }), 400
        
        logger.info(f"Processing text of length: {len(input_text)}")
        
        # Call your model's simplification function
        # Replace 'simplify_text' with your actual method name
        simplified_text = model.text_simplification(input_text)
        
        return jsonify({
            'success': True,
            'original': input_text,
            'simplified': simplified_text
        })
        
    except Exception as e:
        logger.error(f"Error during text simplification: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your text. Please try again.'
        }), 500
    
    
@app.route('/simplify-wikipedia', methods=['POST'])
def simplify_wikipedia():
    """Handle Wikipedia article simplification requests"""
    try:
        # Get Wikipedia URL or title from form
        wiki_input = request.form.get('wiki_input', '').strip()
        use_full_content = request.form.get('use_full_content') == 'true'
        
        if not wiki_input:
            return jsonify({
                'success': False,
                'error': 'Please provide a Wikipedia URL or article title'
            }), 400
        
        logger.info(f"Processing Wikipedia input: {wiki_input}")
        
        # Extract Wikipedia content
        try:
            wiki_data = extract_wikipedia_content(wiki_input)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
        
        # Choose content to simplify
        content_to_simplify = wiki_data['full_content'] if use_full_content else wiki_data['summary']
        
        if not content_to_simplify:
            return jsonify({
                'success': False,
                'error': 'No content found in the Wikipedia article'
            }), 400
        
        # Check content length
        if len(content_to_simplify) > 50000:  # Adjust limit as needed
            return jsonify({
                'success': False,
                'error': 'Article is too long. Try using summary mode or a shorter article.'
            }), 400
        
        logger.info(f"Simplifying content of length: {len(content_to_simplify)}")
        
        # Call your model's simplification function
        simplified_text = model.text_simplification(content_to_simplify)
        
        return jsonify({
            'success': True,
            'original_title': wiki_data['title'],
            'original_url': wiki_data['url'],
            'original_content': content_to_simplify,
            'simplified_content': simplified_text,
            'content_type': 'full_article' if use_full_content else 'summary'
        })
        
    except Exception as e:
        logger.error(f"Error during Wikipedia simplification: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing the Wikipedia article. Please try again.'
        }), 500

@app.route('/health')
def health_check():
    #Simple health check endpoint
    return jsonify({
        'status': 'healthy',
        'model_loaded': model is not None
    })

if __name__ == '__main__':
    print("="*50)
    print("STARTING FLASK SERVER")
    print("="*50)
    print("Server will run on http://0.0.0.0:5000")
    print("Press CTRL+C to stop the server")
    print("="*50)
    # Run the Flask app
    try:
        app.run(
            debug=True, 
            host='0.0.0.0', 
            port=5000, 
            threaded=True,
        )
    except Exception as e:
        print(f"Error starting Flask server: {e}")
        traceback.print_exc()