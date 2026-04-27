import subprocess
with open("old.py", "wb") as f:
    f.write(subprocess.check_output(['git', 'show', 'HEAD~1:ai_evaluator.py']))
with open("old2.py", "wb") as f:
    f.write(subprocess.check_output(['git', 'show', 'HEAD~2:ai_evaluator.py']))
