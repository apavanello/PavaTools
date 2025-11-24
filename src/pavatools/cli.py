import sys
from streamlit.web import cli as stcli
import os

def main():
    # Get the path to the Home page script
    # Assuming this script is run as 'pavatools' and 1_Home.py is in the same package
    package_dir = os.path.dirname(os.path.abspath(__file__))
    home_script = os.path.join(package_dir, "1_Home.py")
    
    # Construct the command
    sys.argv = ["streamlit", "run", home_script] + sys.argv[1:]
    
    # Run streamlit
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()
