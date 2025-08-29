from os import getenv, makedirs, path, listdir, sep
from pathlib import Path
import re, hashlib, cv2

import numpy as np
from werkzeug.utils import secure_filename
from flask import jsonify, current_app, request

from web.apis.utils.serializers import error_response

# Define a regular expression pattern for valid filenames (excluding illegal characters)
valid_filename_pattern = re.compile(r'^[a-zA-Z0-9_.]+$')

def clean_filename(filename):
    # Replace spaces with underscores and remove illegal characters
    cleaned_filename = re.sub(r'[^a-zA-Z0-9_.-]', '', filename)
    cleaned_filename = cleaned_filename.replace(' ', '_')
    cleaned_filename = cleaned_filename.replace('-', '_')
    return cleaned_filename

def uploader(file, upload_subdir=None, dimensions=None):
    """
    Secure file upload handler with proper URL generation
    Args:
        file: File object to upload
        upload_subdir: Subdirectory within media root
        dimensions: Optional tuple (width, height) for image resizing
    Returns: (url, error) tuple
    """
    try:
        # Validate input
        if not file or not file.filename:
            return None, "No file selected"

        # Get configuration
        media_root = Path(current_app.root_path) / current_app.config['MEDIA_LOCATION'].strip('/')
        host_url = request.host_url.rstrip('/')
        
        # Create upload directory structure
        upload_rel_path = Path(upload_subdir.replace('\\', '/')) if upload_subdir else Path('products')
        upload_full_path = (media_root / upload_rel_path).resolve()
        upload_full_path.mkdir(parents=True, exist_ok=True)

        # Generate secure filename
        orig_filename = secure_filename(file.filename)
        name, ext = path.splitext(orig_filename)
        file_hash = hashlib.md5(file.read()).hexdigest()
        file.seek(0)  # Reset file pointer

        # Create unique filename
        unique_name = f"{name[:50]}_{file_hash[:8]}{ext.lower()}"
        save_path = upload_full_path / unique_name

        # Check for existing file
        if save_path.exists():
            url_path = Path(current_app.config['MEDIA_LOCATION']) / upload_rel_path / unique_name
            clean_url = str(url_path).replace('\\', '/')
            clean_url = f"/{clean_url}".replace('//', '/')
            return f"{host_url}{clean_url}", None

        # Process and save file
        if ext.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp']:
            img = cv2.imdecode(np.frombuffer(file.read(), np.uint8), -1)
            if img is None:
                raise ValueError("Invalid image file")
            
            # Resize if dimensions are provided, otherwise keep original size
            if dimensions:
                img = cv2.resize(img, dimensions)
            cv2.imwrite(str(save_path), img)
        else:  # Handle videos and other files
            file.save(str(save_path))

        # Generate clean URL
        url_path = Path(current_app.config['MEDIA_LOCATION']) / upload_rel_path / unique_name
        clean_url = str(url_path).replace('\\', '/')
        clean_url = f"/{clean_url}".replace('//', '/')
        return f"{host_url}{clean_url}", None

    except Exception as e:
        current_app.logger.error(f"Upload error: {str(e)}")
        return None, f"File upload failed: {str(e)}"


# def uploader(file, upload_dir=None):
#     """
#     Uploads any kind of file and returns its full accessible URL.
#     """
#     try:
#         if not file or not file.filename:
#             raise ValueError("Please choose a file to upload")

#         file_content = file.read()
#         file_hash = hashlib.md5(file_content).hexdigest()

#         # Use configured upload folder
#         upload_folder = upload_dir or path.join(
#             current_app.root_path, 
#             f"{getenv('IMAGES_LOCATION', 'uploads')}/uploads"
#         )
        
#         if not path.exists(upload_folder):
#             makedirs(upload_folder, exist_ok=True)

#         # Prepare file path
#         _, file_extension = path.splitext(file.filename)
#         cleaned_filename = secure_filename(file.filename.rsplit('.', 1)[0]).lower()
#         file_name = f"{cleaned_filename}_{file_hash}{file_extension.lower()}"
#         full_path = path.join(upload_folder, file_name)

#         # Save file (handle image/video/svg)
#         if file_extension.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp']:
#             img = cv2.imdecode(np.frombuffer(file_content, np.uint8), -1)
#             if img is None:
#                 raise ValueError("Invalid image format")
#             img = cv2.resize(img, (200, 300), interpolation=cv2.INTER_AREA)
#             cv2.imwrite(full_path, img)
#         else:
#             with open(full_path, 'wb') as f:
#                 f.write(file_content)

#         # Build public URL (accessible from other domains)
#         domain = getenv("APP_DOMAIN", "http://localhost:5001")  # Your server domain
#         # Calculate relative path from server root to the uploaded file
#         relative_path = path.relpath(full_path, current_app.root_path)
#         # Convert OS path separators to URL format
#         url_path = relative_path.replace(sep, '/')
#         public_url = f"{domain}/{url_path}"
        
#         return public_url  # Return full accessible URL

#     except Exception as e:
#         raise Exception(f"Error processing the file: {str(e)}")

# def uploader(file, upload_dir=None):
#     """
#     Uploads any kind of file and returns its full domain URL.
#     """
#     try:
#         if file and file.filename:
#             file_content = file.read()
#             file_hash = hashlib.md5(file_content).hexdigest()

#             # Use configured upload folder
#             upload_folder = upload_dir or path.join(current_app.root_path, f"{getenv('IMAGES_LOCATION')}/uploads")
#             if not path.exists(upload_folder):
#                 makedirs(upload_folder, exist_ok=True)

#             # Prepare file path
#             _, file_extension = path.splitext(file.filename)
#             cleaned_filename = secure_filename(file.filename.rsplit('.', 1)[0]).lower()
#             file_name = f"{cleaned_filename}{file_extension.lower()}"
#             full_path = path.join(upload_folder, file_name)

#             # Save file (handle image/video/svg)
#             if file_extension.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp']:
#                 img = cv2.imdecode(np.frombuffer(file_content, np.uint8), -1)
#                 if img is None:
#                     raise ValueError("Invalid image format")
#                 img = cv2.resize(img, (200, 300), interpolation=cv2.INTER_AREA)
#                 cv2.imwrite(full_path, img)
#             else:
#                 with open(full_path, 'wb') as f:
#                     f.write(file_content)

#             # ✅ Build public URL
#             domain = getenv("APP_DOMAIN", "http://localhost:5001")
#             relative_path = path.relpath(full_path, current_app.root_path)
#             public_url = f"{domain}/{relative_path.replace(sep, '/')}"
            
#             return public_url  # return full accessible link

#         return error_response("Please choose a file to upload")

#     except Exception as e:
#         return error_response(f"Error processing the file: {str(e)}")


# def uploader_0(file, upload_dir=None):
#     """ 
#     Uploads any kind of file/media/image/format ['.jpg', '.jpeg', '.png', '.webp', '.svg', '.gif', '.bmp'].
    
#     Parameters:
#         file: The file to upload.
#         upload_dir: Optional. Custom directory to upload the file to. Defaults to 'static/images/uploads'.
    
#     Returns:
#         str: The full path of the uploaded file if successful, error message otherwise.
#     """
#     try:
#         if file and file.filename:
#             file_content = file.read()
#             file_hash = hashlib.md5(file_content).hexdigest()

#             # Set default upload directory if not provided
#             upload_folder = upload_dir or path.join(current_app.root_path, f"{getenv('IMAGES_LOCATION')}/uploads")
            
#             if not path.exists(upload_folder):
#                 makedirs(upload_folder, exist_ok=True)  # Ensure the directory exists

#             output_size = (200, 300)
#             existing_files = listdir(upload_folder)
            
#             # Extract the original filename (without extension)
#             _, file_extension = path.splitext(file.filename)
#             cleaned_filename = secure_filename(file.filename.rsplit('.', 1)[0]).lower()  # Clean the filename
#             file_name = f"{cleaned_filename}{file_extension.lower()}"
#             full_path = path.join(upload_folder, file_name)

#             # Check for existing files
#             if file_name in existing_files:
#                 return full_path  # Return the full path if the file already exists
            
#             for existing_file in existing_files:
#                 existing_file_path = path.join(upload_folder, existing_file)
#                 if path.isfile(existing_file_path):
#                     with open(existing_file_path, 'rb') as ef:
#                         existing_file_content = ef.read()
#                         existing_file_hash = hashlib.md5(existing_file_content).hexdigest()
#                         if existing_file_hash == file_hash:
#                             return existing_file_path  # Return the full path of the existing file

#             # Handle different file types
#             if file_extension.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp']:
#                 img = cv2.imdecode(np.frombuffer(file_content, np.uint8), -1)
#                 if img is None:
#                     raise ValueError("Invalid image format")
#                 img = cv2.resize(img, output_size, interpolation=cv2.INTER_AREA)
#                 cv2.imwrite(full_path, img)
#             elif file_extension.lower() in ['.mp4', '.mov', '.webm', '.avi']:
#                 with open(full_path, 'wb') as video_file:
#                     video_file.write(file_content)
#             elif file_extension.lower() == '.svg':
#                 with open(full_path, 'wb') as svg_file:
#                     svg_file.write(file_content)
#             else:
#                 raise ValueError("Unsupported file format")

#             return full_path  # Return the full file path of the uploaded file

#         return error_response('Please choose a file to upload')
    
#     except (ValueError, Exception) as e:
#         return error_response(f"Error processing the file: {str(e)}")


def uploader_BAK(file):
    try:
        """ 
        uploads any kind of file/media/image/format ['.jpg', '.jpeg', '.png', '.webp', '.svg' '.gif', '.bmp'] 
        Returns: the uploaded file-name
        """
        
        if file and file.filename:

            file_content = file.read()
            file_hash = hashlib.md5(file_content).hexdigest()
            upload_folder = path.join(current_app.root_path, 'static/images/uploads')
            output_size = (200, 300)
            existing_files = listdir(upload_folder)
            
            # Extract the original filename (without extension)
            _, f_ext = path.splitext(file.filename)
            filename = clean_filename(_).lower()  # Clean the filename
            # Create the final filename by preserving the original file extension
            file_name = secure_filename(filename + f_ext).lower()
            mpath = path.join(upload_folder, file_name)

            if file_name in existing_files:
                # File with the same name already exists, return the existing filename
                return file_name
            
            for filename in existing_files:
                if path.isfile(path.join(upload_folder, filename)):
                    existing_file_content = open(path.join(upload_folder, filename), 'rb').read()
                    existing_file_hash = hashlib.md5(existing_file_content).hexdigest()
                    if existing_file_hash == file_hash:
                        return filename

            if f_ext.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.svg' '.gif', '.bmp']:
                img = cv2.imdecode(np.frombuffer(file_content, np.uint8), -1)
                if img is None:
                    raise ValueError("Invalid image format")
                img = cv2.resize(img, output_size, interpolation=cv2.INTER_AREA)
                cv2.imwrite(mpath, img)
            elif f_ext.lower() in ['.mp4', '.mov', '.webm', '.avi']:
                with open(mpath, 'wb') as video_file:
                    video_file.write(file_content)
            elif f_ext.lower() == '.svg':
                # Save SVG files as-is
                with open(mpath, 'wb') as svg_file:
                    svg_file.write(file_content)
            else:
                raise ValueError("Unsupported File(Image/Video) Format")

            return file_name

        return jsonify({
            'success': True,
            'error': f'Please choose a file to upload',
            'link': f"{request.refferer}"  # Assuming referring_url is a valid URL
        })
    
    except (ValueError, Exception) as e:
        flash(f'Error processing the file: {str(e)}', 'alert-danger')
        return jsonify({
            'error': f'Error processing the file: {e}',
            'flash': 'alert-danger'
        })

def uploader_BAK2(file, upload_dir=None):
    try:
        """ 
        Uploads any kind of file/media/image/format ['.jpg', '.jpeg', '.png', '.webp', '.svg', '.gif', '.bmp'] 
        Parameters:
            file: The file to upload.
            upload_dir: Optional. Custom directory to upload the file to. Defaults to 'static/images/uploads'.
        Returns:
            The uploaded file-name.
        """
        
        if file and file.filename:
            file_content = file.read()
            file_hash = hashlib.md5(file_content).hexdigest()

            # Set default upload directory if not provided
            upload_folder = upload_dir or path.join(current_app.root_path, f"{getenv('IMAGES_LOCATION')}/uploads")
            
            if not path.exists(upload_folder):
                makedirs(upload_folder)  # Ensure the directory exists

            output_size = (200, 300)
            existing_files = listdir(upload_folder)
            
            # Extract the original filename (without extension)
            _, f_ext = path.splitext(file.filename)
            filename = clean_filename(_).lower()  # Clean the filename
            file_name = secure_filename(filename + f_ext).lower()
            mpath = path.join(upload_folder, file_name)

            if file_name in existing_files:
                return file_name
            
            for existing_file in existing_files:
                if path.isfile(path.join(upload_folder, existing_file)):
                    existing_file_content = open(path.join(upload_folder, existing_file), 'rb').read()
                    existing_file_hash = hashlib.md5(existing_file_content).hexdigest()
                    if existing_file_hash == file_hash:
                        return existing_file

            if f_ext.lower() in ['.jpg', '.jpeg', '.png', '.webp', '.svg', '.gif', '.bmp']:
                img = cv2.imdecode(np.frombuffer(file_content, np.uint8), -1)
                if img is None:
                    raise ValueError("Invalid image format")
                img = cv2.resize(img, output_size, interpolation=cv2.INTER_AREA)
                cv2.imwrite(mpath, img)
            elif f_ext.lower() in ['.mp4', '.mov', '.webm', '.avi']:
                with open(mpath, 'wb') as video_file:
                    video_file.write(file_content)
            elif f_ext.lower() == '.svg':
                with open(mpath, 'wb') as svg_file:
                    svg_file.write(file_content)
            else:
                raise ValueError("Unsupported File(Image/Video) Format")

            return file_name

        return error_response('Please choose a file to upload')
    
    except (ValueError, Exception) as e:
        return error_response(f"Error processing the file: {str(e)}")

