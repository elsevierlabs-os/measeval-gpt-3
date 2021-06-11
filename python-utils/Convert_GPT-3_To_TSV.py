#
# Program to take the structured output from our OpenAI GPT-3 driver and convert it into the TSV format expected
# by the MeasEval scoring script
#
# Note:  There are many cases where GPT-3 appears to have gotten into a loop repeating itself on output until
# it hits the token length limit. This can potentially boost/degrade the performance numbers unfairly. We'll have 
# to run the MEasEval dedupe notebook to remove them in order to get a like to like comparison with other 
# MeasEval contestant entries.

# Note: GPT-3 at times will return different-cased strings from what is in the actual paragraphs but at other
# times it preserves the case sensitivity. Currently, we enforce case sensitivity when trying to find a match
# location for a GPT-3 span in the submitted paragraph as we populate TSV fields GPT-3 couldn't generate. This
# effectively drops those mis-cased annotations even though all that is wrong is case sensitivity.
# We could loosen this constraint in the future, but have decided to keep it for now.

import json
import argparse

# Get command line args
parser = argparse.ArgumentParser()

parser.add_argument("resultFile", help="GPT-3 output file from previous step")
parser.add_argument("paragraphDirectory", help="directory containing the paragraphs that were submitted to GPT-3 to create the resultsFile")
parser.add_argument("tsvDirectory", help="Directory to place the MeasEval TSV format files into")

args = parser.parse_args()

resultFile = args.resultFile
paragraphDirectory = args.paragraphDirectory
tsvDirectory = args.tsvDirectory


# Initialize work variables
numQuantityDropped = 0
numUnitDropped = 0
numPropertyDropped = 0
numEntityDropped = 0

workEntity = ''
workEntityOffset = -1
workUnit = ''
workQuantity = ''
workQuantityOffset = -1
workProperty = ''
workPropertyOffset = -1
workAnnotSet = 1
workAnnotId = 1

# Output dubug when running
DEBUG = False

# Reset our work variables
def resetWorkVars():
    global workEntity, workEntityOffset, workUnit, workQuantity, workQuantityOffset, workProperty, workPropertyOffset
    workEntity = ''
    workEntityOffset = -1
    workUnit = ''
    workQuantity = ''
    workQuantityOffset = -1
    workProperty = ''
    workPropertyOffset = -1

# Convert our raw GPT-3 output records to MeasEval TSV format. In our case, an annotation set (which is really
# what we are processing here) should have a quantity along with an optional unit, property, and entity.
def generateTsvAnnots():
    global workEntity, workEntityOffset, workUnit, workQuantity, workQuantityOffset, workProperty, workPropertyOffset, workAnnotSet, workAnnotId, doc_id, numQuantityDropped, numUnitDropped, numPropertyDropped, numEntityDropped
    workAnnots = []
    workStr = ''
    quantityId = -1
    propertyId = -1
    
    # formats for the MeasEval TSV format for the various annotation types.
    QUANTITY_FMT = '''{}\t{}\tQuantity\t{}\t{}\t{}\t{}\t'''
    ENTITY_FMT = '''{}\t{}\tMeasuredEntity\t{}\t{}\t{}\t{}\t{{"{}":"{}"}}'''
    PROPERTY_FMT = '''{}\t{}\tMeasuredProperty\t{}\t{}\t{}\t{}\t{{"HasQuantity":"{}"}}'''
    
    # strip off the string suffix to get just the docId 
    doc_id = doc_id.replace('.txt','')
    
    # Do we have a Quantity for this annotation set? Remember, we might have reset the Quantity to '' because it didn't
    # exist in the actual paragraph being processed
    if (workQuantity != ''):
        workStr = QUANTITY_FMT.format(doc_id, workAnnotSet, workQuantityOffset, len(workQuantity) + workQuantityOffset, workAnnotId, workQuantity)
        if  workUnit != '':
            workStr = workStr + '{ "unit": "' + workUnit + '"}'
        quantityId = workAnnotId
        workAnnotId = workAnnotId+ 1
        workAnnots.append(workStr)
    if (workProperty != ''):
        # MeasuredProperties require both a Measured Entity and Quantity.  Drop any Properties that GPT-3 might have 
        # found without those additional fields
        if workQuantity != '':
            workStr = PROPERTY_FMT.format(doc_id, workAnnotSet, workPropertyOffset, len(workProperty) + workPropertyOffset, workAnnotId, workProperty, quantityId, '\n') 
            propertyId = workAnnotId
            workAnnotId = workAnnotId+ 1
            workAnnots.append(workStr)
        else:
            print("WARNING: Dropping a property because we don't have either/both of an associated Quantity or Entity")
            numPropertyDropped += 1
            workProperty = ''
    if workEntity != '':
        # Entities require at least a Quantity to relate them to. There may also be an optional Property. Depending on
        # what is present in the Annotation Set, we output it with the proper relationship mapping.
        if workQuantity != '':
            if workProperty != '':
                workStr = ENTITY_FMT.format(doc_id, workAnnotSet, workEntityOffset, len(workEntity) + workEntityOffset, workAnnotId, workEntity, "HasProperty", propertyId) 
            else:
                workStr =  ENTITY_FMT.format(doc_id, workAnnotSet, workEntityOffset, len(workEntity) + workEntityOffset, workAnnotId, workEntity, "HasQuantity", quantityId)
            workAnnotId = workAnnotId+ 1
            workAnnots.append(workStr)
        else:
            print("WARNING: Dropping an Entity because we don't have an associated Quantity.")
            numEntityDropped += 1
    
    resetWorkVars()
    return workAnnots
    


with open(resultFile) as f:
  rawdata = f.read()
  
  # Note: we had to do some additional massaging of the results generated by our GPT-3 driver. Specifically, Python's
  # JSON parsing didn't seem to like the embedded \n characters even through the strings passed other JSON validators.
  data = rawdata.replace('\n', '\\n')
  data = data.replace(',\\n', ',\n')
  data = data.replace('\\n"\\n}', '"}')
  data = data.replace('"\\n}', '"}')
  data = data.replace('}\\n]}\\n', '}]}')
  
  if DEBUG == True:
    print("Massaged GPT-3 Results: "  +  data)
  
  # Turn our string into a JSON Object
  jsonData = json.loads(data)

  
  results = jsonData['results']

  # Let's process each result in the JSON structure. Each should correspond to 1 paragraph we submitted
  # and will have a docId, a finish code ("stop" or "length") from GPT-3, and a formatted "text: " section
  # for the returned text from GPT-3. The text should consist of a formatted "Data:" section consisting of
  # predicted "Quantity", "Property", and "Entity" where applicable.
    
  # Note: There was at least one response I saw where GPT-3 erroneously output some text before falling into 
  # the Data: pattern.
  for result in results:
    doc_id = result['doc']
    finish_reason = result['finish_reason']
    text = result['text']
    # Every annotation in the TSV file has a unique annotation id. We reset the id at each new paragraph.
    workAnnotId = 1
    # All the related annotations are in an unique annotation set for the paragraph. We reset that annotation
    # set id for each paragraph
    workAnnotSet = 1
    outputStr = ''
    outputAnnots = []
    
    if DEBUG == True:
      print("########################################################")
      print("processing doc: " + doc_id)
      print("finish_reason: " + finish_reason)
    
    # Read in the paragraph text that was submitted to OpenAI so we can calculate the offsets needed for the TSV
    with open (paragraphDirectory + doc_id) as para_file:
        # Create the TSV file we're going to create for the raw results file
        with open(tsvDirectory + doc_id.replace('.txt', '.tsv'), 'w') as tsv_file:
            # Put out the TSV file header
            tsv_file.write('{}\n'.format('docId\tannotSet\tannotType\tstartOffset\tendOffset\tannotId\ttext\tother'))
            
            para = para_file.read()
            if DEBUG == True:
                print('Original Para: ' + para)
            # New paragraph so reset all the work variables    
            resetWorkVars()
            
            # process the lines from the text predictions from GPT-3 and start building up the TSV records. Each line
            # should be an annotation of some sort
            predictionLines = text.strip().split('\n')
            for line in predictionLines:
                if line.startswith("Data:") == True:
                    # Skip the "Data:"" line
                    x = 0
                elif line.startswith('Quantity: '):
                    workQuantity = line.split("Quantity: ",1)[1]
                    workQuantityOffset = para.find(workQuantity)
                    # GPT-3 sometimes goes off the reservation and returns text that isn't in the original paragraph
                    # Sometimes extra characters, sometimes completely different text. This is true for all 3 types
                    # of annotations.
                    # We'll drop the Quantity if that is the case:
                    if workQuantityOffset == -1:
                        print("WARNING: Quantity not in original para: " + workQuantity)
                        numQuantityDropped += 1
                        workQuantity = ''

                elif line.startswith('Unit: '):
                    workUnit = line.split("Unit: ",1)[1]
                    if para.find(workUnit) == -1:
                        print("WARNING: Unit not in original para: " + workUnit)
                        numUnitDropped += 1
                        workUnit = ''
                elif line.startswith('Entity: '):
                    workEntity = line.split("Entity: ",1)[1]
                    workEntityOffset = para.find(workEntity)
                    if workEntityOffset == -1:
                        print("WARNING: Entity not in original para: " + workEntity)
                        numEntityDropped += 1
                        workEntity = ''
                elif line.startswith('Property: '):
                    workProperty = line.split("Property: ",1)[1]
                    workPropertyOffset = para.find(workProperty)
                    if workPropertyOffset == -1:
                        print("WARNING: Property not in original para: " + workProperty)
                        numPropertyDropped += 1
                        workProperty = ''
                # If we've moved onto a new annotation set for the same paragraph
                # format the data for the TSV file and save it off for writing out later.
                elif line.startswith(''):
                    outputAnnots.extend(generateTsvAnnots())
                    workAnnotSet = workAnnotSet + 1
                else:
                    print("unknown line type:'" + line +"'")
            # Pick up the last annot in the file to convert (if there is one)
            if (workQuantity != ''):
                outputAnnots.extend(generateTsvAnnots())
            
            if DEBUG == True:
              print('writing out TSV file to disk.')
                
            for annot in outputAnnots:
                if DEBUG == True:
                    print(annot)
                tsv_file.write('{}\n'.format(annot))
        
            
  print("Final dropped annotation counts:")
  print('================================')
  print('''Number of Quantity annotations dropped: {}'''.format(numQuantityDropped))
  print('''Number of Unit annotations dropped: {}'''.format(numUnitDropped))
  print('''Number of Property annotations dropped: {}'''.format(numPropertyDropped))
  print('''Number of Entity annotations dropped: {}'''.format(numEntityDropped))
