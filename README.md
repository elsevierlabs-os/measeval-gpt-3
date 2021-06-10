# measeval-gpt-3

This repo contains various Python utility code and notebooks related to the evaluation of OpenAi's GPT-3 on SemEval 2021 - Task 8, MeasEval.  In order to generate actual GPT-3 predictions you will need an API key from OpenAI. 

The process of evaluating the MeasEval datasets agasint GPT-3 is a mult-step process. 


1. Submit MeaseEval Evaluation paragraphs to GPT-3

The python driver to submit paragraphs (along with bath few shot prompts) is located in the python-gpt3 directory. The measEvalDriver.py program will process a keyfile containing a list of paragraph files to process. It will append each target paragraph to a provided base prompt, submit it to GPT-3, and then saves the JSON results from OpenAI into a local file (there is one output file created for each keyfile processed). In our case, we submitted a local copy of the Evaluation paragraphs from the MeasEval task (https://github.com/harperco/MeasEval/tree/main/data/eval/text). The program takes 6 command line parameters:

- "keyfilePath" - directory containing they keyfiles to process
- "keyfileName" - paragraph keys file name to process
- "paragraphDirectory" - directory containing the paragraphs referenced in the keyfiles to process
- "basePromptFile" - text file containing the base few-shot prompt that the target paragraph is appended to")
- "resultsDirectory" - directory in which to place the GPT-3 JSON output
- "api_key" - OpenAI API key

Our raw results from the MeasEval eval paragraphs are located in this repo in the .... directory

2. Convert GPT-3 JSON response format into MeasEval TSV format

The MeaseEval evaluation script expects its input to be a specific TSV format. We use the Convert_GPT-3_To_TSV.py program to convert the files created in the previous step output into this format. The program will process an output file from step 1. It converts them to the MeasEval TSV format, and populates some of the data and types that we were unable to get GPT-3 to create. This is detailed in our paper. The program creates a TSV file for each paragraph contained in the JSON input file. 

The program takes 3 command line parameters

- resultsFile - GPT-3 output file from previous step
- paragraphDirectory - directory containing the paragraphs that were submitted to GPT-3 to create the resultsFile
- tsvDirectory - Directory to place the MeasEval TSV format files into

Our converted results are located in this repo in the x......  directory 

3. Remove potential duplicate ....

4. Run the actual MeasEval evaluation script




Citing
If you need to cite this software in your own work, please use the following DOI.

Kohler, Curt and Harper, Corey (2021), Elsevier Labs. MeasEval GPT-3 Utilities [Computer Software]; https://github.com/elsevierlabs-os/measeval-gpt-3.

