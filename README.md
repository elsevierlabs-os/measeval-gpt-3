# MeasEval GPT-3 Utilities

This repo contains various Python utility code and iPython notebooks related to the evaluation of OpenAi's GPT-3 on SemEval 2021 - Task 8, MeasEval. The details of our investigation can be found on the ArXiv paper: XXXXXXXXXX. In order to actually evaluate your own GPT-3 predictions you will need an API key from OpenAI to generate results from their service.  We are including the outputs from our investigation here as an example.

The process of evaluating the MeasEval datasets against GPT-3 is a mult-step process. 


1. Submit MeaseEval Evaluation paragraphs to GPT-3

The python driver to submit paragraphs (along with bath few shot prompts) is located in the python-gpt3 directory. The measEvalDriver.py program will process a keyfile containing a list of paragraph files to process. It will append each target paragraph to a provided base prompt, submit it to GPT-3, and then saves the JSON results from OpenAI into a local file (there is one output file created for each keyfile processed). In our case, we submitted a local copy of the Evaluation paragraphs from the MeasEval task (https://github.com/harperco/MeasEval/tree/main/data/eval/text). The program takes 6 command line parameters:

- "keyfilePath" - directory containing they keyfiles to process
- "keyfileName" - paragraph keys file name to process
- "paragraphDirectory" - directory containing the paragraphs referenced in the keyfiles to process
- "basePromptFile" - text file containing the base few-shot prompt that the target paragraph is appended to")
- "resultsDirectory" - directory in which to place the GPT-3 JSON output
- "api_key" - OpenAI API key

The keyset groupings we ran are located in this repo in the 'keys' directory and the corresponding raw results from the MeasEval eval paragraphs are located in the 'outputs/gpt3-results' directory.

2. Convert GPT-3 JSON response format into MeasEval TSV format

The  evaluation script from MeasEval (https://github.com/harperco/MeasEval/tree/main/eval) expects its input to be a specific TSV format. We use the Convert_GPT-3_To_TSV.py program to convert the files created in the previous step output into this format. The program will process an output file from step 1. It converts them to the MeasEval TSV format, and populates some of the data and types that we were unable to get GPT-3 to create. This is detailed in our paper. The program creates a TSV file for each paragraph contained in the JSON input file. 

The program takes 3 command line parameters

- resultsFile - GPT-3 output file from previous step
- paragraphDirectory - directory containing the paragraphs that were submitted to GPT-3 to create the resultsFile
- tsvDirectory - Directory to place the MeasEval TSV format files into

Our converted TSV results are located in this repo in the 'outputs/tsv'  directory 

3. Remove potential duplicate annotations.

When running our GPT-3 scripts we noticed a number of cases where the output woudl repeatedly output the same annotation sequences multiple times. Due to the way that the MeasEval evaluation script operates, that could have the effect of artifically increasing or decreasing the final scores. In order to address this issue, we post-processed the TSV-format annotation files to drop any identical annotation sets. We'd like to thank Corey Harper for providing the MeasEval iPython Notebook that we used for this step. 

The Notebook needs 3 parameters updated in cell 2:

- submissions - base directory for the MeasEval submission(s)
- inputSub - subdireectory that has the input TSV annotation files to de-duplicate
- outputSub - subdirectory to write the de-duplicated TSV annotation files to

Our de-duplicated TSV files are located in this repo in the 'outputs/tsv_dedupe' folder.

4. Run the actual MeasEval evaluation script agasint our TSV files. Code and instructions can be found at: https://github.com/harperco/MeasEval/tree/main/eval.


