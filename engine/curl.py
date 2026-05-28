import subprocess
import shutil
from pathlib import Path
from typing import Dict, Optional


def check_curl_available() -> bool:
    try:
        result = shutil.which('curl')
        if result:
            return True
        result = shutil.which('curl.exe')
        if result:
            return True
        return False
    except Exception:
        return False


def curl_capability(args: Dict, working_dir: Path) -> Dict:
    url = args.get('url', '')
    method = args.get('method', 'GET').upper()
    headers = args.get('headers', {})
    data = args.get('data', '')
    timeout = args.get('timeout', 30)
    follow_redirects = args.get('follow_redirects', True)
    verbose = args.get('verbose', False)
    output_file = args.get('output_file', '')
    
    if not url:
        return {"error": "URL is required"}
    
    if not isinstance(timeout, int) or timeout < 1:
        timeout = 30
    elif timeout > 300:
        timeout = 300
    
    curl_exe = shutil.which('curl') or shutil.which('curl.exe')
    if not curl_exe:
        return {"error": "curl not found in PATH"}
    
    cmd_args = [curl_exe]
    
    cmd_args.extend(['-X', method])
    
    if follow_redirects:
        cmd_args.append('-L')
    
    cmd_args.extend(['-s', '-S'])
    
    if verbose:
        cmd_args.append('-v')
    
    for key, value in headers.items():
        cmd_args.extend(['-H', f'{key}: {value}'])
    
    if data:
        cmd_args.extend(['-d', data])
    
    cmd_args.extend(['--connect-timeout', str(timeout)])
    cmd_args.extend(['--max-time', str(timeout * 2)])
    
    if output_file:
        cmd_args.extend(['-o', str(Path(output_file))])
    
    cmd_args.append(url)
    
    try:
        result = subprocess.run(
            cmd_args,
            cwd=str(working_dir),
            capture_output=True,
            text=True,
            timeout=timeout * 3
        )
        
        response = {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "success": result.returncode == 0,
            "url": url,
            "method": method,
            "timeout_used": timeout
        }
        
        if output_file and result.returncode == 0:
            output_path = Path(output_file)
            if output_path.exists():
                response["output_file"] = str(output_path)
                response["output_size"] = output_path.stat().st_size
        
        return response
    except subprocess.TimeoutExpired:
        return {"error": f"请求超时（{timeout}秒）", "url": url}
    except Exception as e:
        return {"error": str(e), "url": url}