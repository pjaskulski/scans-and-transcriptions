# Scans and Transcriptions

Do you have a collection of scanned manuscripts or typescripts? Would you like them transcribed? This simple **desktop** application makes it easy to use Gemini for this purpose. Once the transcriptions are complete, you can review, verify and correct them.

The process is straightforward: you prepare a folder containing scans of manuscripts, typescripts and old prints, and the application uses various Gemini models to produce the transcriptions. It assists in the verification process by enabling visual comparison of the scans and transcriptions, providing voice recordings and offering named entity recognition (NER) — errors are more likely to occur in proper names. Finally, you will receive a folder containing the scans, the transcription files in TXT format, the MP3 voice recordings and the metadata saved in JSON files.

Since the application uses models via the API, this is subject to a fee in accordance with Google's current [price list](https://ai.google.dev/gemini-api/docs/pricing). 

The Gemini Pro 3 model is used for transcription, while the Gemini Flash 2.5 TTS model generates audio recordings (TTS) and the Gemini Pro 3 Image model (also known as Nano Banana Pro) locates proper names on a scan. The application can prepare transcriptions for a single image or a series of files. The Gemini API key should be stored in the `.env` file as the `GEMINI_API_KEY` environment variable, or in the `config/config.json` file under the `api_key` field.


## Application features:

  - **Browsing scans and transcriptions**. The application assumes that the specified directory contains scan files and transcript files with identical names but with the *.txt extension. If a text file is missing, the application will automatically create an empty one.
  - **Creating transcripts using the LLM model** (Gemini Pro 3, internet access required) for the current scan or scan series. For scan series, the application displays all scans in the selected directory and selects those that do not yet have a text transcript file or those with an empty transcript file. This selection can, of course, be changed.
  - You can perform transcriptions using one of the **predefined prompts** (prompts for Polish documents are currently available), or you can prepare your own prompt.
  - Transcription files are automatically saved when you move to the next/previous file. You can also force a save by pressing the SAVE button.
  - Transcriptions can be saved as a **bulk text file** or in a **docx file**. For docx files, the application also concatenates broken words and lines into paragraphs. Transcriptions can also be saved in **TEI-XML** format. 
  - To facilitate verification of transcription accuracy, the application allows you to pan the scan using the left mouse button, **zoom in/out** using the mouse scroll wheel, and display a **magnifying glass** window at a selected location using the right mouse button. 
  - Simple **filters** can be applied to scans, such as contrast enhancement and image inversion.
  - A feature that aids verification is the ability to **read the transcript aloud**. This feature, like transcriptions, requires internet access (the Gemini TTS model is used).
  - You can adjust the font size in the transcription field.
  - Due to transcription errors often appearing in proper names (e.g. people, places and institutions), the option to **highlight** such words (**NER** button) has been added to draw attention to them during transcription verification. An experimental function (BOX button) **automatically marks entity names** in the scan. These names are marked with frames, and transcription text is placed above the frame, for a quick assessment of transcription accuracy. The size and position of the frames for entity names can be adjusted. The list of found **entity names can be exported to a CSV file** for further use.
  - The application **records the cost of all API calls** for the current catalogue, providing information about the date, the model used, the number of tokens used (input and output), and the cost of the call. It also summarizes the cost for the entire current scan catalogue.
  - The user interface supports **multiple language versions**. Currently, two languages are defined: **PL** and **EN** (see the localization.json file for definitions). 


## Screenshots and description:

The application window shows a magnifying glass with a visible enlargement of the fragment:

![Screen](/doc/screen_scan_transcript.png)

In the left panel containing the scan, you can move the image using the left mouse button, zoom in/out using the mouse wheel and enlarge a fragment using the magnifying glass icon and the right mouse button.

The application window is visible while Gemini is reading the scan (the progress bar is visible at the top of the right panel and the Gemini button is unavailable while the model is processing the image).

![Screen](/doc/screen_scan_transcript_przetwarzanie.png)

In the right panel of the application, above the text field, there is a bar displaying the name of the scan directory that is currently being viewed (processed). To the right of this is a button that allows you to change the folder. Clicking this button displays a folder selection window and then loads the scan and transcription files (txt, if they are already in the folder). The same folder selection window appears automatically when the application starts.

![Screen](/doc/images_folder.png)

**Main toolbar**:

List of buttons:

  - Go to the first file
  - Go to the previous file
  - Save changes to the current file
  - Read a scan with Gemini
  - Read a series of scans with Gemini
  - Save the read text for all files in a merged txt file
  - Save the read text for all files in a merged docx file
  - Save the read text for all files in a TEI-XML file
  - Go to the next file
  - Go to the last file

![Screen](/doc/toolbar.png)

Below the list of buttons, you will find information about the currently selected prompt file. The buttons on the right allow you to change, create or edit a prompt. When creating a new prompt, the application will suggest a template.

If there is no transcription file for the current file, an empty file will be created automatically. Transcription files can be edited manually. As well as saving via the 'SAVE' button, files are automatically saved when moving to the next or previous file, and when exiting the application.

You can also close the application using the Ctrl+Q shortcut.

**Transcription toolbar**:

![Screen](/doc/image_info.png)

Below is a bar displaying information about the current scan file, including its name, number in the series and the total number of scans in the folder. To the right are the 'A+' and 'A-' buttons, which are used to adjust the font size in the text field. Between the scan file name and the font size adjustment buttons is a search field for the transcription. After entering the required text and pressing Enter, the application highlights the matching text. You can also use the arrow button to start the search. The button with the 'x' symbol removes the highlights and clears the search field. The drop-down menu on the right allows you to change the interface language. Currently, Polish and English versions are available.

The second row of the toolbar contains buttons for reading the transcription aloud: “>” (Read) starts reading, “■” stops it and “||” pauses it. The Gemini TTS model supports 24 languages and automatically recognises the transcription language.

The 'NER', 'BOX' and 'CLS' buttons help to verify the transcription. Due to the high frequency of errors in proper names, these can be marked in the transcription text ('NER') and, for comparison, on the scan ('BOX'). The 'CLS' button clears the markings. The 'LEG' button displays a legend with descriptions of the colours used to mark different categories of proper names (people, places and organisations).
The 'CSV' button allows you to export all the proper names found in the current catalogue to a CSV file.
The 'LOG' button displays a list of all API calls, along with their cost.
The 'FIX' button activates an experimental feature that verifies the existing transcription and highlights sections that may contain errors. This verification process uses the same Gemini model as the original transcription.
  
**Reading a series of scans** by the Gemini model:

![Screen](/doc/screen_scan_transcript_seria.png)

The file batch reading window displays all the scan files in the directory. You can select which files Gemini will read. By default, files for which there is no transcribed text file yet, or only an empty one, are selected. Buttons at the bottom of the window allow you to select or deselect all scans and initiate the transcription process for the selected scans. A progress bar will be displayed during this process (processing multiple files can be time-consuming).

Example of a **typescript transcription**:

![Screen](/doc/typescript_example.jpg)

**Prompt editor**:

![Screen](/doc/prompt_editor.jpg)

**Highlighting** of entity names in the transcription text:

![Screen](/doc/highlighting_entity_names.jpg)

Transcription errors produced by the LLM model often affect proper names. To make them easier to find, an experimental BOX function has been developed **to mark entity names in the scan**. The names are marked with frames and the name read by the model is placed above the frame. This allows you to quickly compare the name with the scan's actual content. See the screenshot below.

Although automatic marking is fairly accurate, it's possible to adjust the created frames. To do this, grab the frame with the left mouse button to move it or adjust its size. The lower right corner of the frame is a handle that allows you to resize it. The new position or size is automatically saved when you release the mouse button. However, it's important to remember that the main purpose of this feature is to indicate the position of the proper name for visual verification of transcription accuracy, even if the indication is inaccurate.

![Screen](/doc/entity_names_on_scan.jpg)

Here is an example of **colour coding** different categories of entity names (PERSON, LOCATION, ORGANISATION):

![Screen](/doc/entity_names_on_scan_2.jpg)

In some cases, manual reading of a scan can be facilitated by **image filters**. The following filters are available: negative and contrast. The screenshot below shows the negative filter in use:

![Screen](/doc/screen_scan_transcript_filtr.jpg)

Here is an example of the transcription of an **old print** from 18th-century Poland:

![Screen](/doc/screen_scan_transcript_print.jpg)

**API cost control** for the current catalogue:

![Screen](/doc/cost_control.jpg)

English **language version**:

![Screen](/doc/screen_english.jpg)

A 20th-century manuscript in German is shown here.

![Screen](/doc/screen_htr_ger.png)

Can Gemini read documents from the early 17^(th) century? A specialist should assess the number of errors and distortions – below is an example of a [letter](https://polona2.pl/item/list-marcina-glogowskiego-do-macieja-lubienskiego-8-luty-1608,OTIzNzMwMTA/0/#info:metadata) from 1608 (Marcin Głogowski to Maciej Łubieński).

![Screen](/doc/screen_glogowski_1608.jpg)

The 'test' folder contains sample scans and transcripts, including scans of manuscripts and typescripts from the 18th, 19th and 20th centuries, as well as old prints from the 18th century. Most of the documents are in Polish.

Please note that access to the Gemini Pro 3 model via API **is subject to a fee**, as stated on the Google pricing page.

The Gemini model was involved in the application programming :-)

The project was carried out at the Digital History Lab of the Institute of History at the Polish Academy of Sciences [https://ai.ihpan.edu.pl](https://ai.ihpan.edu.pl).

**Note**: A similar but more advanced transcription application (also using Python and TKinter!) is 
[Transcription Pearl](https://github.com/mhumphries2323/Transcription_Pearl) (Mark Humphries and Lianne C. Leddy, 2024. Transcription Pearl 1.0 Beta. Department of History: Wilfrid Laurier University.) – it allows you to use various models from OpenAI, Google, and Anthropic, import images from PDF files, etc. The same authors have another application: [ArchiveStudio](https://github.com/mhumphries2323/Archive_Studio), which is designed for the Windows system.


## Installation

Ensure you have Python installed (version 3.10 or newer is recommended).
Install the required libraries:

```
pip install -r requirements.txt
```

## Configuration 

API key: Create a .env file in the main application directory and add your Gemini key to it: 

```
GEMINI_API_KEY=your_key_here
```

**Prompts**: The content of the instructions for the AI model (prompts) should be located in .txt files in the ../prompt/ subdirectory. This directory already contains sample prompts.

**Settings**: The application stores preferences (font size, user interface language) in the config.json file. You can also save your API key in the ‘api_key’ field in this file. The application first looks for the GEMINI_API_KEY environment variable, and if it is not found, it tries to load the key from the config.json file.

