#
# Program to take the structured output from our OpenAI GPT-3 driver and convert it into the
# TSV format expected by the MeasEval scoring script
#
# Note:  There are many cases where GPT-3 appears to have gotten into a loop repeating itself
# on output until it hits the token length limit. This can potentially boost/degrade the
# performance numbers unfairly. We'll have to run the MEasEval dedupe notebook to remove them
# in order to get a like to like comparison with other MeasEval contestant entries.

# Note: GPT-3 at times will return different-cased strings from what is in the actual
# paragraphs but at other times it preserves the case sensitivity. Currently, we enforce
# case sensitivity when trying to find a match location for a GPT-3 span in the submitted
# paragraph as we populate TSV fields GPT-3 couldn't generate. This effectively drops
# those mis-cased annotations even though all that is wrong is case sensitivity. We could
# loosen this constraint in the future, but have decided to keep it for now.

import json
import argparse

# Get command line args
parser = argparse.ArgumentParser()

parser.add_argument("resultFile", help="GPT-3 output file from previous step")
parser.add_argument("paragraphDirectory",
                    help="directory containing the paragraphs that were submitted to GPT-3")
parser.add_argument("tsvDirectory",
                    help="Directory to place the MeasEval TSV format files into")

args = parser.parse_args()

resultFile = args.resultFile
paragraphDirectory = args.paragraphDirectory
tsvDirectory = args.tsvDirectory

# Initialize work variables
NUM_QUANTITY_DROPPED = 0
NUM_UNIT_DROPPED = 0
NUM_PROPERTY_DROPPED = 0
NUM_ENTITY_DROPPED = 0

WORK_ENTITY = ''
WORK_ENTITY_OFFSET = -1
WORK_UNIT = ''
WORK_QUANTITY = ''
WORK_QUANTITY_OFFSET = -1
WORK_PROPERTY = ''
WORK_PROPERTY_OFFSET = -1
WORK_ANNOT_SET = 1
WORK_ANNOT_ID = 1

DOC_ID = ''

# Output dubug when running
DEBUG = False


# Reset our work variables
def reset_work_vars():
    global WORK_ENTITY, WORK_ENTITY_OFFSET, WORK_UNIT, WORK_QUANTITY, WORK_QUANTITY_OFFSET, \
        WORK_PROPERTY, WORK_PROPERTY_OFFSET
    WORK_ENTITY = ''
    WORK_ENTITY_OFFSET = -1
    WORK_UNIT = ''
    WORK_QUANTITY = ''
    WORK_QUANTITY_OFFSET = -1
    WORK_PROPERTY = ''
    WORK_PROPERTY_OFFSET = -1


# Convert our raw GPT-3 output records to MeasEval TSV format. In our case, an annotation
# set (which is really what we are processing here) should have a quantity along with an
# optional unit, property, and entity.
def generate_tsv_annots():
    global WORK_ENTITY, WORK_ENTITY_OFFSET, WORK_UNIT, WORK_QUANTITY, WORK_QUANTITY_OFFSET,\
        WORK_PROPERTY, WORK_PROPERTY_OFFSET, WORK_ANNOT_SET, WORK_ANNOT_ID, DOC_ID, \
        NUM_QUANTITY_DROPPED, NUM_UNIT_DROPPED, NUM_PROPERTY_DROPPED, NUM_ENTITY_DROPPED
    work_annots = []
    work_str = ''
    quantity_id = -1
    property_id = -1

    # formats for the MeasEval TSV format for the various annotation types.
    quantity_fmt = '''{}\t{}\tQuantity\t{}\t{}\t{}\t{}\t'''
    entity_fmt = '''{}\t{}\tMeasuredEntity\t{}\t{}\t{}\t{}\t{{"{}":"{}"}}'''
    property_fmt = '''{}\t{}\tMeasuredProperty\t{}\t{}\t{}\t{}\t{{"HasQuantity":"{}"}}'''

    # strip off the string suffix to get just the docId
    DOC_ID = DOC_ID.replace('.txt', '')

    # Do we have a Quantity for this annotation set? Remember, we might have reset the
    # Quantity to '' because it didn't exist in the actual paragraph being processed
    if WORK_QUANTITY != '':
        work_str = quantity_fmt.format(DOC_ID, WORK_ANNOT_SET, WORK_QUANTITY_OFFSET,
                                       len(WORK_QUANTITY) + WORK_QUANTITY_OFFSET,
                                       WORK_ANNOT_ID, WORK_QUANTITY)
        if WORK_UNIT != '':
            work_str = work_str + '{ "unit": "' + WORK_UNIT + '"}'
        quantity_id = WORK_ANNOT_ID
        WORK_ANNOT_ID = WORK_ANNOT_ID + 1
        work_annots.append(work_str)
    if WORK_PROPERTY != '':
        # MeasuredProperties require both a Measured Entity and Quantity.  Drop any Properties
        # that GPT-3 might have found without those additional fields
        if WORK_QUANTITY != '':
            work_str = property_fmt.format(DOC_ID, WORK_ANNOT_SET, WORK_PROPERTY_OFFSET,
                                           len(WORK_PROPERTY) + WORK_PROPERTY_OFFSET, WORK_ANNOT_ID,
                                           WORK_PROPERTY, quantity_id, '\n')
            property_id = WORK_ANNOT_ID
            WORK_ANNOT_ID = WORK_ANNOT_ID + 1
            work_annots.append(work_str)
        else:
            print("WARNING: Dropping a property because we don't have either/both "
                  "of an associated Quantity or Entity")
            NUM_PROPERTY_DROPPED += 1
            WORK_PROPERTY = ''
    if WORK_ENTITY != '':
        # Entities require at least a Quantity to relate them to. There may also be an optional
        # Property. Depending on what is present in the Annotation Set, we output it with the
        # proper relationship mapping.
        if WORK_QUANTITY != '':
            if WORK_PROPERTY != '':
                work_str = entity_fmt.format(DOC_ID, WORK_ANNOT_SET, WORK_ENTITY_OFFSET,
                                             len(WORK_ENTITY) + WORK_ENTITY_OFFSET, WORK_ANNOT_ID,
                                             WORK_ENTITY, "HasProperty", property_id)
            else:
                work_str = entity_fmt.format(DOC_ID, WORK_ANNOT_SET, WORK_ENTITY_OFFSET,
                                             len(WORK_ENTITY) + WORK_ENTITY_OFFSET, WORK_ANNOT_ID,
                                             WORK_ENTITY, "HasQuantity", quantity_id)
            WORK_ANNOT_ID = WORK_ANNOT_ID + 1
            work_annots.append(work_str)
        else:
            print("WARNING: Dropping an Entity because we don't have an associated Quantity.")
            NUM_ENTITY_DROPPED += 1

    reset_work_vars()
    return work_annots


with open(resultFile) as f:
    rawdata = f.read()

    # Note: we had to do some additional massaging of the results generated by our GPT-3
    # driver. Specifically, Python's JSON parsing didn't seem to like the embedded '\n'
    # characters even through the strings passed other JSON validators.
    data = rawdata.replace('\n', '\\n')
    data = data.replace(',\\n', ',\n')
    data = data.replace('\\n"\\n}', '"}')
    data = data.replace('"\\n}', '"}')
    data = data.replace('}\\n]}\\n', '}]}')

    if DEBUG is True:
        print("Massaged GPT-3 Results: " + data)

    # Turn our string into a JSON Object
    json_data = json.loads(data)

    results = json_data['results']

    # Let's process each result in the JSON structure. Each should correspond to 1 paragraph
    # we submitted and will have a docId, a finish code ("stop" or "length") from GPT-3, and
    # a formatted "text: " section for the returned text from GPT-3. The text should consist of
    # a formatted "Data:" section consisting of predicted "Quantity", "Property", and "Entity"
    # where applicable.

    # Note: There was at least one response I saw where GPT-3 erroneously output some text
    # before falling into the Data: pattern.
    for result in results:
        DOC_ID = result['doc']
        finish_reason = result['finish_reason']
        text = result['text']
        # Every annotation in the TSV file has a unique annotation id. We reset the id at
        # each new paragraph.
        WORK_ANNOT_ID = 1
        # All the related annotations are in an unique annotation set for the paragraph.
        # We reset that annotation set id for each paragraph
        WORK_ANNOT_SET = 1
        outputStr = ''
        outputAnnots = []

        if DEBUG is True:
            print("########################################################")
            print("processing doc: " + DOC_ID)
            print("finish_reason: " + finish_reason)

        # Read in the paragraph text that was submitted to OpenAI so we can calculate the
        # offsets needed for the TSV
        with open(paragraphDirectory + DOC_ID) as para_file:
            # Create the TSV file we're going to create for the raw results file
            with open(tsvDirectory + DOC_ID.replace('.txt', '.tsv'), 'w') as tsv_file:
                # Put out the TSV file header
                tsv_file.write('{}\n'
                               .format('docId\tannotSet\tannotType\tstartOffset\tendOffset\t'
                                       'annotId\ttext\tother'))

                para = para_file.read()
                if DEBUG is True:
                    print('Original Para: ' + para)
                # New paragraph so reset all the work variables
                reset_work_vars()

                # process the lines from the text predictions from GPT-3 and start building
                # up the TSV records. Each line should be an annotation of some sort
                prediction_lines = text.strip().split('\n')
                for line in prediction_lines:
                    if line.startswith("Data:") is True:
                        # Skip the "Data:"" line
                        pass
                    elif line.startswith('Quantity: '):
                        WORK_QUANTITY = line.split("Quantity: ", 1)[1]
                        WORK_QUANTITY_OFFSET = para.find(WORK_QUANTITY)
                        # GPT-3 sometimes goes off the reservation and returns text that isn't
                        # in the original paragraph Sometimes extra characters, sometimes
                        # completely different text. This is true for all 3 types of annotations.
                        # We'll drop the Quantity if that is the case:
                        if WORK_QUANTITY_OFFSET == -1:
                            print("WARNING: Quantity not in original para: " + WORK_QUANTITY)
                            NUM_QUANTITY_DROPPED += 1
                            WORK_QUANTITY = ''

                    elif line.startswith('Unit: '):
                        WORK_UNIT = line.split("Unit: ", 1)[1]
                        if para.find(WORK_UNIT) == -1:
                            print("WARNING: Unit not in original para: " + WORK_UNIT)
                            NUM_UNIT_DROPPED += 1
                            WORK_UNIT = ''
                    elif line.startswith('Entity: '):
                        WORK_ENTITY = line.split("Entity: ", 1)[1]
                        WORK_ENTITY_OFFSET = para.find(WORK_ENTITY)
                        if WORK_ENTITY_OFFSET == -1:
                            print("WARNING: Entity not in original para: " + WORK_ENTITY)
                            NUM_ENTITY_DROPPED += 1
                            WORK_ENTITY = ''
                    elif line.startswith('Property: '):
                        WORK_PROPERTY = line.split("Property: ", 1)[1]
                        WORK_PROPERTY_OFFSET = para.find(WORK_PROPERTY)
                        if WORK_PROPERTY_OFFSET == -1:
                            print("WARNING: Property not in original para: " + WORK_PROPERTY)
                            NUM_PROPERTY_DROPPED += 1
                            WORK_PROPERTY = ''
                    # If we've moved onto a new annotation set for the same paragraph
                    # format the data for the TSV file and save it off for writing out later.
                    elif line.startswith(''):
                        outputAnnots.extend(generate_tsv_annots())
                        WORK_ANNOT_SET = WORK_ANNOT_SET + 1
                    else:
                        print("unknown line type:'" + line + "'")
                # Pick up the last annot in the file to convert (if there is one)
                if WORK_QUANTITY != '':
                    outputAnnots.extend(generate_tsv_annots())

                if DEBUG is True:
                    print('writing out TSV file to disk.')

                for annot in outputAnnots:
                    if DEBUG is True:
                        print(annot)
                    tsv_file.write('{}\n'.format(annot))

    print("Final dropped annotation counts:")
    print('================================')
    print('''Number of Quantity annotations dropped: {}'''.format(NUM_QUANTITY_DROPPED))
    print('''Number of Unit annotations dropped: {}'''.format(NUM_UNIT_DROPPED))
    print('''Number of Property annotations dropped: {}'''.format(NUM_PROPERTY_DROPPED))
    print('''Number of Entity annotations dropped: {}'''.format(NUM_ENTITY_DROPPED))
