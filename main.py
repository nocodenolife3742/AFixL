from AfixL.controller import Controller
from pathlib import Path

# TODO : Use argparse to get the project directory and mode

if __name__ == "__main__":
    project_dir = Path("D:/fuzz_example/")
    controller = Controller(project_dir, 2)
    controller.run_main()
    
