# gtranslate_cli
Google Translate is a fabulous tool, but we are hardcore hackers and resent the browser. As such, we’d like to use the command line for doing string translation. At the same time, we are polyglots and know multiple languages (RO, IT, EN, DE). What we want is a CLI tool that can translate between Romanian, Italian, German and English. The tool will read input data from a file and output the translation to the console. The output language is specified as a flag on the command line.

### Notes:
- use this program in linuxOS or macOS
- you need to have a GCP service account that has access to the Google TranslationAPI
(for instructions to generate Gooogle Translate API credentials, please follow the short tutorial [here](https://codelabs.developers.google.com/codelabs/cloud-translation-python3#0)

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

