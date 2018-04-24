import pytextrank
import sys
import json
import re
reload(sys)
sys.setdefaultencoding('utf-8')

inputs = "ris.json"
path_stage1 = "o1.json"

ris_string = json.load(open(inputs))
pattern = re.compile("TI  - (.*?)\\r|AB  - (.*?)\\r")
matches = re.findall(pattern, ris_string['ris'])
all_inputs = []
for section in matches:
       all_inputs.append((''.join([word + ' ' for word in section])).strip())

input_json = {}
input_json['id'] = "0"
input_json['text'] = '.'.join(all_inputs)

with open('ris.json', 'w') as output:
    json.dump(input_json, output)

with open(path_stage1, 'w') as f:
    for graf in pytextrank.parse_doc(pytextrank.json_iter(inputs)):
        pytextrank.pretty_print(graf._asdict())
        f.write("%s\n" % pytextrank.pretty_print(graf._asdict()))

# In[]:

path_stage1 = "o1.json"
path_stage2 = "o2.json"

graph, ranks = pytextrank.text_rank(path_stage1)
pytextrank.render_ranks(graph, ranks)

with open(path_stage2, 'w') as f:
    for rl in pytextrank.normalize_key_phrases(path_stage1, ranks):
        f.write("%s\n" % pytextrank.pretty_print(rl._asdict()))

# In[]:

path_stage1 = "o1.json"
path_stage2 = "o2.json"
path_stage3 = "o3.json"

kernel = pytextrank.rank_kernel(path_stage2)

with open(path_stage3, 'w') as f:
    for s in pytextrank.top_sentences(kernel, path_stage1):
        f.write(pytextrank.pretty_print(s._asdict()))
        f.write("\n")

# In[]:

path_stage2 = "o2.json"
path_stage3 = "o3.json"

phrases = "\n".join(set([p for p in pytextrank.limit_keyphrases(path_stage2, phrase_limit=10)]))
sent_iter = sorted(pytextrank.limit_sentences(path_stage3, word_limit=150), key=lambda x: x[1])
s = []

for sent_text, idx in sent_iter:
    s.append(pytextrank.make_sentence(sent_text))

graf_text = " ".join(s)
print 'keywords:\n' + phrases
