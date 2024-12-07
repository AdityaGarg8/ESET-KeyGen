from .SharedTools import console_log, INFO, OK, ERROR, WARN
from .ProgressBar import ProgressBar, DEFAULT_RICH_STYLE

import argparse
import requests
import zipfile
import pathlib
import sys
import os

class Updater:
    def __init__(self, from_main=False):
        self.from_main = from_main
        self.arch = None
        if sys.platform.startswith('win'):
            self.arch = 'win32'
            if sys.maxsize > 2**32: # 64bit 
                self.arch = 'win64'
        elif sys.platform == 'darwin':
            arch = 'macos' # prefix for universal macOS builds (arm64 + x86_64)
            #arch = 'macos_arm64'
            #if platform.machine() == "x86_64":
            #    arch = 'macos_amd64'
        self.releases = None
    
    def get_releases(self, version='latest'):
        url = 'https://api.github.com/repos/rzc0d3r/ESET-KeyGen/releases'
        if version == 'latest':
            url = 'https://api.github.com/repos/rzc0d3r/ESET-KeyGen/releases/latest'
        try:
            response = requests.get(url, timeout=5)
            update_json = response.json()
            try:
                if update_json.get('message') is not None:
                    console_log('Your IP address has been blocked. try again later or use a VPN!', ERROR)
                    return None
            except AttributeError:
                pass
            if version == 'latest': # when requesting the latest version, the site returns json without a list. 
                update_json = [update_json]
            f_update_json = {}
            for release in update_json:
                f_update_json[release['name']] = {
                    'version': release['name'],
                    'src': release['zipball_url'],
                    'assets': {},
                    'changelog': release['body'].strip()
                }
                for asset in release['assets']:
                    f_update_json[release['name']]['assets'][asset['name']] = asset['browser_download_url']
            return f_update_json
        except:
            return None

    def find_suitable_data(self, datatype='source_code', version='latest'): # datatype: source_code OR executable_file
        if self.releases is None:
            self.releases = self.get_releases(version)
        if version == 'latest':
            if datatype == 'source_code':
                return self.releases[list(self.releases.keys())[0]]['src']
            elif datatype == 'executable_file':
                assets = self.releases[list(self.releases.keys())[0]]['assets']
        else:
            for release_name in self.releases:
                if release_name == version:
                    if datatype == 'source_code':
                        return self.releases[release_name]['src']
                    elif datatype == 'executable_file':
                        assets = self.releases[release_name]['assets']
                        break
        if datatype == 'executable_file':
            for asset_name, asset_url in assets.items():
                if asset_name.find(self.arch) != -1:
                    return asset_url
        
    def download_file(self, url):
        try:
            response = requests.get(url, stream=True)
            try:
                filename = response.headers.get('content-disposition').split('filename=')[1]
                console_log(f'Downloading {filename}...', INFO)
            except:
                pass
            total_length = response.headers.get('content-length')
            if total_length is None: # No content length header
                with open(filename, 'wb') as f:
                    f.write(response.content)
            else:
                task = ProgressBar(int(total_length), '           ', DEFAULT_RICH_STYLE)
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk: # filter out keep-alive new chunks
                            f.write(chunk)
                            task.update(len(chunk))
                            task.render()
            return str(pathlib.Path(filename).resolve())
        except Exception as e:
            console_log(f"Error downloading file: {e}", ERROR)
            return False
    
    def extract_data(self, data_path: str, new_name=None):
        extracted_data_path = None
        if data_path.endswith('.zip'): # source code
            try:
                with zipfile.ZipFile(data_path, 'r') as zipf:
                    extracted_folder_name = zipf.filelist[0].filename[0:-1] # rzc0d3r-ESET-KeyGen-56a2c5b/ -> rzc0d3r-ESET-KeyGen-56a2c5b
                    zipf.extractall()
                    console_log("Extraction completed successfully!", OK)
                    extracted_data_path = str(pathlib.Path(extracted_folder_name).resolve())
                if new_name is not None:
                    os.rename(extracted_folder_name, new_name)
                    extracted_data_path = str(pathlib.Path(new_name).resolve())
                else:
                    os.rename(extracted_folder_name, 'ESET-KeyGen-'+data_path.split('-')[3]) # rzc0d3r-ESET-KeyGen-v1.5.2.7-0-g344f0d9.zip -> ESET-KeyGen-v1.5.2.7
                    extracted_data_path = 'ESET-KeyGen-'+data_path.split('-')[3]
            except zipfile.BadZipFile:
                console_log("Downloaded file is not a valid zip file!", ERROR)
            except FileExistsError as e:
                console_log(str(e), ERROR)
        if not data_path.endswith('.zip'): # executable file
            extracted_data_path = str(pathlib.Path(data_path).resolve())
            if new_name is not None:
                os.rename(data_path, new_name)
                extracted_data_path = str(pathlib.Path(new_name).resolve())
        console_log(f"Location of update: {extracted_data_path}", WARN)
        return extracted_data_path
    
def updater_main(from_main=False):
    args = {}
    if not from_main:
        print(sys.argv)
        args_parser = argparse.ArgumentParser()
        args_parser.add_argument('--version', type=str, default='latest', help='Specify the version to be installed')
        args_parser.add_argument('--custom-json', type=str, default='', help='Specify a custom path to the json file with update data')
        args_parser.add_argument('--src', action='store_true', help='Download source code instead of binary files')
        args_parser.add_argument('--list', action='store_true', help='Shows which versions are available')
        args_parser.add_argument('--output-filename', type=str, default='', help='')
        args = vars(args_parser.parse_args())
    else:
        args = {
            'version': 'latest',
            'custom_json': '',
            'src': False,
            'list': False,
            'output_filename': ''
        }
    update_json = parse_update_json(args['custom_json'])
    if args['list']:
        for release in update_json:
            print(release)
        sys.exit(1)
    if update_json is None:
        console_log("Failed to parse update JSON!", ERROR)
        sys.exit(1)
    update_data = get_assets_from_version(update_json, args['version'])
    if update_data is not None:
        if args['src']:
            update_src_code(update_data)
        else:
            update_binary(update_data, output_filename=args['output_filename'])
    else:
        console_log(f"Version {args['version']} not found!", ERROR)

if __name__ == '__main__':
    updater_main()