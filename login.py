import server
from comfy.cli_args import args
from aiohttp_session import setup, get_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from aiohttp import web
from aiohttp.web_request import Request
from jinja2 import Environment, FileSystemLoader, select_autoescape
import base64
from os import path, urandom
import folder_paths
from datetime import datetime, timedelta
from .config import fs_config

node_dir = path.dirname(__file__)
comfy_dir = path.dirname(folder_paths.__file__)
template_dir = path.join(node_dir, "template")
secret_key_path = path.join(node_dir,'.secret-key.txt')
login_html_path = path.join(template_dir, "login.html")
login_css_path = path.join(template_dir, "login.css")
KEY_AGE_LIMIT = timedelta(days=30)  # Key expiration period

# Global cache dictionary
user_dict = {
    u.user_name: u.password for u in fs_config.auth.users
}
token_set = { token for token in fs_config.auth.tokens }

def generate_key():
    return base64.urlsafe_b64encode(urandom(32)).decode('utf-8')

def write_key_to_file(key):
    with open(secret_key_path, 'w') as file:
        file.write(f"{key},{datetime.now().isoformat()}")

def read_key_from_file():
    try:
        with open(secret_key_path, 'r') as file:
            key, timestamp = file.read().split(',')
            return key, datetime.fromisoformat(timestamp)
    except FileNotFoundError:
        return None, None

def key_is_old(timestamp):
    return datetime.now() - timestamp > KEY_AGE_LIMIT

def get_or_refresh_key():
    key, timestamp = read_key_from_file()
    if key is None or timestamp is None or key_is_old(timestamp):
        key = generate_key()
        write_key_to_file(key)
    return key

# Access the PromptServer instance and its app
prompt_server = server.PromptServer.instance
app = prompt_server.app
routes = prompt_server.routes

secret_key = get_or_refresh_key()
setup(app, EncryptedCookieStorage(secret_key))

#app.route.add_static('/login/', template_dir)

@routes.get("/login")
async def get_root(request: Request):
    session = await get_session(request)
    wrong_password = request.query.get('wrong_password', '')
    if 'logged_in' in session and session['logged_in']:
        raise web.HTTPFound('/')
    else:
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        template = env.get_template('login.html')

        #first_time = not os.path.exists(password_path)
        #username, _ = get_user_data() if not first_time else (None, None)
        #prompt_for_username = False

        #if username is None and not first_time:
        #    # If there's no username but it's not the first time, prompt for username
        #    prompt_for_username = True

        login_rendered = template.render(
            #first_time=first_time,
            #username=username,
            disabled=not fs_config.auth.enabled,
            wrong_password=wrong_password,
            #prompt_for_username=prompt_for_username
        )
        return web.Response(text=login_rendered, content_type='text/html')

@routes.get("/login.css")
async def get_login_css(request: Request):
    return web.FileResponse(login_css_path)

@routes.post("/login")
async def login_handler(request: Request):
    data = await request.post()
    username_input = data.get('username')
    password_input = data.get('password') #.encode('utf-8')

    real_password = user_dict.get(username_input)

    if real_password is None:
        return web.HTTPNotFound()#'User not found'

    if real_password != password_input:
        print(f"wrong password, got {password_input}, expected {real_password}")
        return web.HTTPFound('/login?wrong_password=1')

    # Password is correct
    session = await get_session(request)
    session['logged_in'] = True
    session['username'] = username_input

    # # Existing user login attempt
    # if password_cached and bcrypt.checkpw(password_input, password_cached):
    # # New user setup
    # salt = bcrypt.gensalt()
    # hashed_password = bcrypt.hashpw(password_input, salt)

    return web.HTTPFound('/')  # Redirect to the main page if the password is correct

@routes.get("/logout")
async def get_root(request):
    session = await get_session(request)
    session['logged_in'] = False
    session.pop('username', None)  # Clear the username
    response = web.HTTPFound('/login')  # Redirect to the main page if the password is correct
    return response

async def process_request(request, handler):
    """Process the request by calling the handler and setting response headers."""
    response = await handler(request)
    if request.path == '/':  # Prevent caching the main page after logout
        response.headers.setdefault('Cache-Control', 'no-cache')
    return response

@web.middleware
async def check_login_status(request: web.Request, handler):
    # Skip authentication for specific paths
    if (not fs_config.auth.enabled
            or request.path == '/login'
            or request.path == '/flyingshapes/reload-config'
            or request.path.endswith('.css')
            or request.path.endswith('.css.map')
            or request.path.endswith('.js')
            or request.path.endswith('.ico')):
        return await handler(request)

    session = await get_session(request)
    if 'logged_in' in session and session['logged_in']:
        # User is logged in via session, proceed without checking tokens
        return await process_request(request, handler)

    # Check the Authorization header for Bearer token
    if args.enable_cors_header is None or args.enable_cors_header == '*' or args.enable_cors_header == request.headers.get('Origin'):
        authorization_header = request.headers.get("Authorization")
        if authorization_header:
            auth_type, token_from_header = authorization_header.split()
            if auth_type == 'Bearer' and token_from_header in token_set:
                # Bearer token is valid, proceed without checking query token
                return await process_request(request, handler)

        # Fallback to check the token in the query
        if request.query.get("token") in token_set:
            return await process_request(request, handler)

    # unauthorized access
    accept_header = request.headers.get('Accept', '')
    if 'text/html' in accept_header:
        raise web.HTTPFound('/login')
    else:
        return web.json_response({'error': 'Authentication required.'}, status=401)

app.middlewares.append(check_login_status)