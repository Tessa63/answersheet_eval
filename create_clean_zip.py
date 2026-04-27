import os
import zipfile

def zip_project(folder_path, zip_path):
    print(f"Creating zip file at: {zip_path}")
    
    # Exclude these heavy or unnecessary directories/files
    exclude_dirs = {'.venv', '__pycache__', '.git', 'temp_test', 'scratch'}
    exclude_files = {'answersheet_eval.zip', 'log.txt', 'failover_debug.txt', 'low_eval_debug.json'}
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            # Modify dirs in-place to skip excluded directories
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                if file in exclude_files or file.endswith('.zip'):
                    continue
                    
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                
                # Try to avoid zipping the zipfile itself
                if os.path.abspath(file_path) == os.path.abspath(zip_path):
                    continue
                    
                zipf.write(file_path, arcname)
                
    print(f"Zip created successfully! Size: {os.path.getsize(zip_path) / (1024*1024):.2f} MB")

if __name__ == "__main__":
    project_dir = r"c:\Users\hp\answersheet_eval"
    zip_output = r"c:\Users\hp\answersheet_eval\answersheet_eval_clean.zip"
    zip_project(project_dir, zip_output)
