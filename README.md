# gtranslate_cli
Google Translate is a fabulous tool, but we are hardcore hackers and resent the browser. As such, we’d like to use the command line for doing string translation. At the same time, we are polyglots and know multiple languages (RO, IT, EN, DE). What we want is a CLI tool that can translate between Romanian, Italian, German and English. The tool will read input data from a file and output the translation to the console. The output language is specified as a flag on the command line.

### Notes:
- use this program in linuxOS or macOS
- you need to have a GCP service account that has access to the Google TranslationAPI
(for instructions to generate Gooogle Translate API credentials, please follow the short tutorial [here](https://codelabs.developers.google.com/codelabs/cloud-translation-python3#0)
- I integrated a virtual environment .venv/ in the repo, the user can use it or can create his own with `python -m venv .venv`, run `source .venv/bin/activate` then run the installation of the requirements with `pip install -r requirements.txt'

### Setup:
Step 1:
Type
`git clone https://github.com/cristiciortea/gtranslate_cli.git`
in the shell  

Step 2:
Add path to credential .json file to the environment (.env file) or just export it:

GOOGLE_APPLICATION_CREDENTIALS=<path_to_your_service_account_key_json_file>  
**or**  
export GOOGLE_APPLICATION_CREDENTIALS=[PATH]

![image](https://user-images.githubusercontent.com/74206863/171264753-ef0a8dbb-de37-43ed-a39e-7638ae38859d.png)  

Step 3:
- option one: type in the shell -> 1. `source .venv/bin/activate` -> the run: 2. `./gtd.py` (the daemon will start), then run the command 3. `./gtranslate.py -f <filename> -l <lang> `
- option two: 
---
### Additional notes regarding environment variables file (.env):
- .env variables can be overwritten by the user
- QUERIES_PER_SEC represents max requests per second that the api is allowed to do
- DAEMON_TIMEOUT_MINUTES is the timeout limit of the daemon. After it passed the value there (e.g. 30 minutes) the daemon will shut down.
- DEBUG is the debug mode env variable -> 0 means we are not on debug mode, 1 means debug mode
---
### Sample usage:  
(localhost) $ QUERIES_PER_SEC=10 gtd  
Translation daemon started, throttling at 10 queries/second.  

(localhost) $ gtranslate -f tests/given_sample_text.txt -l en  
Translating, please wait…  
Good morning  
Good evening  
Good day  
Goodbye  
(localhost) $  
