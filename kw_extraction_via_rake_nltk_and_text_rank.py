import re,collections,math,nltk,networkx,itertools,string,sys
from rake_nltk import Rake
from pprint import pprint
	
def normalize(my_x, my_min, my_max):
	try:
		val=(my_x-my_min)/(my_max-my_min)
		return val
	except:
		val=1
		return val

def check_pos(x):

	my_word=x
	list_of_words = x.split()
	my_pos = [x for x in nltk.pos_tag(list_of_words)]
	for i in list(set([x[1] for x in my_pos])):
		if i in ['CD','IN','JJ','NNS','RB','VB','VBG','VBN','VBZ']:
			return False
	return True

def extract_candidate_words(text, good_tags=set(['JJ','JJR','JJS','NN','NNP','NNS','NNPS'])):
	
	punct = set(string.punctuation)
	stop_words = set(nltk.corpus.stopwords.words('english'))
	tagged_words = itertools.chain.from_iterable(nltk.pos_tag_sents(nltk.word_tokenize(sent) for sent in nltk.sent_tokenize(text)))
	candidates = [word.lower() for word, tag in tagged_words if tag in good_tags and word.lower() not in stop_words and not all(char in punct for char in word)]

	return candidates

def score_keyphrases_by_text_rank(text, n_keywords=0.05):
	
	words = [word.lower()
			 for sent in nltk.sent_tokenize(text)
			 for word in nltk.word_tokenize(sent)]
	candidates = extract_candidate_words(text)
	graph = networkx.Graph()
	graph.add_nodes_from(set(candidates))
	def pairwise(iterable):
		a, b = itertools.tee(iterable)
		next(b, None)
		return zip(a, b)
	for w1, w2 in pairwise(candidates):
		if w2:
			graph.add_edge(*sorted([w1, w2]))
	ranks = networkx.pagerank(graph)
	if 0 < n_keywords < 1:
		n_keywords = int(round(len(candidates) * n_keywords))
	word_ranks = {word_rank[0]: word_rank[1]
				  for word_rank in sorted(iter(ranks.items()), key=lambda x: x[1], reverse=True)[:n_keywords]}
	keywords = set(word_ranks.keys())
	keyphrases = {}
	j = 0
	for i, word in enumerate(words):
		if i < j:
			continue
		if word in keywords:
			kp_words = list(itertools.takewhile(lambda x: x in keywords, words[i:i+10]))
			avg_pagerank = sum(word_ranks[w] for w in kp_words) / float(len(kp_words))
			keyphrases[' '.join(kp_words)] = avg_pagerank
			j = i + len(kp_words)
	
	return sorted(iter(keyphrases.items()), key=lambda x: x[1], reverse=True)

def extract_candidate_features(candidates, doc_text, doc_excerpt, doc_title):

	candidate_scores = collections.OrderedDict()
	
	doc_word_counts = collections.Counter(word.lower() for sent in nltk.sent_tokenize(doc_text) for word in nltk.word_tokenize(sent))
	
	for candidate in candidates:
		
		pattern = re.compile(r'\b'+re.escape(candidate)+r'(\b|[,;.!?]|\s)', re.IGNORECASE)
		
		cand_doc_count = len(pattern.findall(doc_text))
		if not cand_doc_count:
			continue
	
		candidate_words = candidate.split()
		max_word_length = max(len(w) for w in candidate_words)
		term_length = len(candidate_words)
		sum_doc_word_counts = float(sum(doc_word_counts[w] for w in candidate_words))
		try:
			if term_length == 1:
				lexical_cohesion = 0.0
			else:
				lexical_cohesion = term_length * (1 + math.log(cand_doc_count, 10)) * cand_doc_count / sum_doc_word_counts
		except (ValueError, ZeroDivisionError) as e:
			lexical_cohesion = 0.0
		
		in_title = 1 if pattern.search(doc_title) else 0
		in_excerpt = 1 if pattern.search(doc_excerpt) else 0
		doc_text_length = float(len(doc_text))
		first_match = pattern.search(doc_text)
		abs_first_occurrence = first_match.start() / doc_text_length
		if cand_doc_count == 1:
			spread = 0.0
			abs_last_occurrence = abs_first_occurrence
		else:
			for last_match in pattern.finditer(doc_text):
				pass
			abs_last_occurrence = last_match.start() / doc_text_length
			spread = abs_last_occurrence - abs_first_occurrence

		candidate_scores[candidate] = {'term_count': cand_doc_count,
									   'term_length': term_length, 'max_word_length': max_word_length,
									   'spread': spread, 'lexical_cohesion': lexical_cohesion,
									   'in_excerpt': in_excerpt, 'in_title': in_title,
									   'abs_first_occurrence': abs_first_occurrence,
									   'abs_last_occurrence': abs_last_occurrence}

	return candidate_scores

def calculate_keywords(text):
	r = Rake(stopwords=["i","me","my","myself","we","our","ours","ourselves","you","your","yours","yourself","yourselves","he","him","his","himself","she","her","hers","herself","it","its","itself","they","them","their","theirs","themselves","what","which","who","whom","this","that","these","those","am","is","are","was","were","be","been","being","have","has","had","having","do","does","did","doing","a","an","the","and","but","if","or","because","as","until","while","of","at","by","for","with","about","against","between","into","through","during","before","after","above","below","to","from","up","down","in","out","on","off","over","under","again","further","then","once","here","there","when","where","why","how","all","any","both","each","few","more","most","other","some","such","no","nor","not","only","own","same","so","than","too","very","s","t","can","will","just","don","should","now"]) # Uses stopwords for english from NLTK, and all puntuation characters.

	#titles and abstracts parsed and saved in json file need to be joined here below
	my_text=re.sub(r'\s\s+',' ',text.lower())

	r.extract_keywords_from_text(my_text)

	kw_rake=r.get_ranked_phrases_with_scores()
	kw_rake=[[x[1],x[0]] for x in kw_rake if len(x[1])>3]
	kw_rake=[x for x in kw_rake if len(x[0].split())<3]
	kw_rake=[x for x in kw_rake if min([len(i) for i in x[0].split()])>3]
	kw_rake=[x for x in kw_rake if not re.search(r'\d',x[0])]
	kw_rake=[x for x in kw_rake if check_pos(x[0]) is True]

	kw_rake_scores=[x[1] for x in kw_rake]
	my_min=min(kw_rake_scores)
	my_max=max(kw_rake_scores)

	kw_rake=[[x[0],normalize(x[1],my_min,my_max)] for x in kw_rake]
	kw_rake=[x for x in kw_rake if x[1]>0.01]

	#text="History and evolution of the arctic flora: in the footsteps of Eric. A major contribution to our initial understanding of the origin, history and biogeography of the present-day arctic flora was made by Eric Hulten in his landmark book Outline of the History of Arctic and Boreal Biota during the Quarternary Period, published in 1937. Here we review recent molecular and fossil evidence that has tested some of Hulten's proposals. There is now excellent fossil, molecular and phytogeographical evidence to support Hulten's proposal that Beringia was a major northern refugium for arctic plants throughout the Quaternary. In contrast, most molecular evidence fails to support his proposal that contemporary east and west Atlantic populations of circumarctic and amphi-Atlantic species have been separated throughout the Quaternary. In fact, populations of these species from opposite sides of the Atlantic are normally genetically very similar, thus the North Atlantic does not appear to have been a strong barrier to their dispersal during the Quaternary. Hulten made no detailed proposals on mechanisms of speciation in the Arctic; however, molecular studies have confirmed that many arctic plants are allopolyploid, and some of them most probably originated during the Holocene. Recurrent formation of polyploids from differentiated diploid or more low-ploid populations provides one explanation for the intriguing taxonomic complexity of the arctic flora, also noted by Hulten. In addition, population fragmentation during glacial periods may have lead to the formation of new sibling species at the diploid level. Despite the progress made since Hulten wrote his book, there remain large gaps in our knowledge of the history of the arctic flora, especially about the origins of the founding stocks of this flora which first appeared in the Arctic at the end of the Pliocene (approximately 3 Ma). Comprehensive analyses of the molecular phylogeography of arctic taxa and their relatives together with detailed fossil studies are required to fill these gaps. Quantification of population sizes of large herbivores and their long-term functional role in ecosystems using dung fungal spores. The relationship between large herbivore numbers and landscape cover over time is poorly understood. There are two schools of thought: one views large herbivores as relatively passive elements upon the landscape and the other as ecosystem engineers driving vegetation succession. The latter relationship has been used as an argument to support reintroductions of large herbivores onto many landscapes in order to increase vegetation heterogeneity and biodiversity through local-scale disturbance regimes. Most of the research examining the relationship between large herbivores and their impact on landscapes has used extant studies. An alternative approach is to estimate the impact of variations in herbivore populations through time using fossil dung fungal spores and pollen in sedimentary sequences. However, to date, there has been little quantification of fossil dung fungal spore records and their relationship to herbivore numbers, leaving this method open to varied interpretations. In this study, we developed further the dung fungal spore method and determined the relationship between spore abundance in sediments (number cm(-2)year(-1)) and herbivore biomass densities (kgha(-1)). To establish this relationship, we used the following: (i) the abundance of Sporormiella spp., Sordaria spp. and Podospora spp. spores in modern sediments from ponds and (ii) weekly counts of contemporary wildlife over a period of 5years from the rewilded site, Oostvaardersplassen, in the Netherlands. Results from this study demonstrate that there is a highly significant relationship between spore abundance and local biomass densities of herbivores that can be used in the calibration of fossil records. Mammal biomass density (comprising Konik horses, Heck cattle and red deer) predicts in a highly significant way the abundance of all dung fungal spores amalgamated together. This relationship is apparent at a very local scale (<10m), when the characteristics of the sampled ponds are taken into account (surface area of pond, length of shoreline). In addition, we identify that dung fungal spores are principally transported into ponds by surface run-off from the shores. These results indicate that this method provides a robust quantitative measure of herbivore population size over time. Herbivory Network: An international, collaborative effort to study herbivory in Arctic and alpine ecosystems. Plant-herbivore interactions are central to the functioning of tundra ecosystems, but their outcomes vary over space and time. Accurate forecasting of ecosystem responses to ongoing environmental changes requires a better understanding of the processes responsible for this heterogeneity. To effectively address this complexity at a global scale, coordinated research efforts, including multi-site comparisons within and across disciplines, are needed. The Herbivory Network was established as a forum for researchers from Arctic and alpine regions to collaboratively investigate the multifunctional role of herbivores in these changing ecosystems. One of the priorities is to integrate sites, methodologies, and metrics used in previous work, to develop a set of common protocols and design long-term geographically-balanced, coordinated experiments. The implementation of these collaborative research efforts will also improve our understanding of traditional human-managed systems that encompass significant portions of the sub-Arctic and alpine areas worldwide. A deeper understanding of the role of herbivory in these systems under ongoing environmental changes will guide appropriate adaptive strategies to preserve their natural values and related ecosystem services. (C) 2016 Elsevier B.V. and NIPR. All rights reserved. Biomass allometry for alder, dwarf birch, and willow in boreal forest and tundra ecosystems of far northeastern Siberia and north-central Alaska. Shrubs play an important ecological role in the Arctic system, and there is evidence from many Arctic regions of deciduous shrubs increasing in size and expanding into previously forb or graminoid-dominated ecosystems. There is thus a pressing need to accurately quantify regional and temporal variation in shrub biomass in Arctic regions, yet allometric equations needed for deriving biomass estimates from field surveys are rare. We developed 66 allometric equations relating basal diameter (BD) to various aboveground plant characteristics for three tall, deciduous shrub genera growing in boreal and tundra ecoregions in far northeastern Siberia (Yakutia) and north-central Alaska. We related BD to plant height and stem, branch, new growth (leaves + new twigs), and total aboveground biomass for alder (Alms viridis subsp. crispa and Alms fruticosa), dwarf birch (Betula nana subsp. exilis and divaricata), and willow (Salix spp.). The equations were based on measurements of 358 shrubs harvested at 33 sites. Plant height (r(2) = 0.48-0.95), total aboveground biomass (r(2) = 0.46-0.99), and component biomass (r(2) = 0.13-0.99) were significantly (P < 0.01) related to shrub BD. Alder and willow populations exhibited differences in allometric relationships across ecoregions, but this was not the case for dwarf birch. The allometric relationships we developed provide a tool for researchers and land managers seeking to better quantify and monitor the form and function of shrubs across the Arctic landscape. (C) 2014 Elsevier B.V. All rights reserved. Shrub expansion may reduce summer permafrost thaw in Siberian tundra. Climate change is expected to cause extensive vegetation changes in the Arctic: deciduous shrubs are already expanding, in response to climate warming. The results from transect studies suggest that increasing shrub cover will impact significantly on the surface energy balance. However, little is known about the direct effects of shrub cover on permafrost thaw during summer. We experimentally quantified the influence of Betula nana cover on permafrost thaw in a moist tundra site in northeast Siberia with continuous permafrost. We measured the thaw depth of the soil, also called the active layer thickness (ALT), ground heat flux and net radiation in 10 m diameter plots with natural B. nana cover (control plots) and in plots in which B. nana was removed (removal plots). Removal of B. nana increased ALT by 9% on average late in the growing season, compared with control plots. Differences in ALT correlated well with differences in ground heat flux between the control plots and B. nana removal plots. In the undisturbed control plots, we found an inverse correlation between B. nana cover and late growing season ALT. These results suggest that the expected expansion of deciduous shrubs in the Arctic region, triggered by climate warming, may reduce summer permafrost thaw. Increased shrub growth may thus partially offset further permafrost degradation by future temperature increases. Permafrost models need to include a dynamic vegetation component to accurately predict future permafrost thaw. Global assessment of nitrogen deposition effects on terrestrial plant diversity: a synthesis. Atmospheric nitrogen (N) deposition is it recognized threat to plant diversity ill temperate and northern parts of Europe and North America. This paper assesses evidence from field experiments for N deposition effects and thresholds for terrestrial plant diversity protection across a latitudinal range of main categories of ecosystems. from arctic and boreal systems to tropical forests. Current thinking on the mechanisms of N deposition effects on plant diversity, the global distribution of G200 ecoregions, and current and future (2030) estimates of atmospheric N-deposition rates are then used to identify the risks to plant diversity in all major ecosystem types now and in the future. This synthesis paper clearly shows that N accumulation is the main driver of changes to species composition across the whole range of different ecosystem types by driving the competitive interactions that lead to composition change and/or making conditions unfavorable for some species. Other effects such its direct toxicity of nitrogen gases and aerosols long-term negative effects of increased ammonium and ammonia availability, soil-mediated effects of acidification, and secondary stress and disturbance are more ecosystem, and site-specific and often play a supporting role. N deposition effects in mediterranean ecosystems have now been identified, leading to a first estimate of an effect threshold. Importantly, ecosystems thought of as not N limited, such as tropical and subtropical systems, may be more vulnerable in the regeneration phase. in situations where heterogeneity in N availability is reduced by atmospheric N deposition, on sandy soils, or in montane areas. Critical loads are effect thresholds for N deposition. and the critical load concept has helped European governments make progress toward reducing N loads on sensitive ecosystems. More needs to be done in Europe and North America. especially for the more sensitive ecosystem types. including several ecosystems of high conservation importance. The results of this assessment Show that the Vulnerable regions outside Europe and North America which have not received enough attention are ecoregions in eastern and Southern Asia (China, India), an important part of the mediterranean ecoregion (California, southern Europe). and in the coming decades several subtropical and tropical parts of Latin America and Africa. Reductions in plant diversity by increased atmospheric N deposition may be more widespread than first thought, and more targeted Studies are required in low background areas, especially in the G200 ecoregions. Meta-analysis of high-latitude nitrogen-addition and warming studies implies ecological mechanisms overlooked by land models. Accurate representation of ecosystem processes in land models is crucial for reducing predictive uncertainty in energy and greenhouse gas feedbacks with the climate. Here we describe an observational and modeling meta-analysis approach to benchmark land models, and apply the method to the land model CLM4.5 with two versions of belowground biogeochemistry. We focused our analysis on the aboveground and belowground responses to warming and nitrogen addition in high-latitude ecosystems, and identified absent or poorly parameterized mechanisms in CLM4.5. While the two model versions predicted similar soil carbon stock trajectories following both warming and nitrogen addition, other predicted variables (e.g., belowground respiration) differed from observations in both magnitude and direction, indicating that CLM4.5 has inadequate underlying mechanisms for representing high-latitude ecosystems. On the basis of observational synthesis, we attribute the model-observation differences to missing representations of microbial dynamics, aboveground and belowground coupling, and nutrient cycling, and we use the observational meta-analysis to discuss potential approaches to improving the current models. However, we also urge caution concerning the selection of data sets and experiments for meta-analysis. For example, the concentrations of nitrogen applied in the synthesized field experiments (average = 72 kg ha(-1) yr(-1)) are many times higher than projected soil nitrogen concentrations (from nitrogen deposition and release during mineralization), which precludes a rigorous evaluation of the model responses to likely nitrogen perturbations. Overall, we demonstrate that elucidating ecological mechanisms via meta-analysis can identify deficiencies in ecosystem models and empirical experiments."

	kw_text_rank=[list(x) for x in (score_keyphrases_by_text_rank(text, n_keywords=0.05))]
	kw_text_rank=[x for x in kw_text_rank if not re.search(r'(study|studi|effect|relation)',x[0])]
	kw_text_rank=[x for x in kw_text_rank if min([len(i) for i in x[0].split()])>3]
	kw_text_rank_scores=[x[1] for x in kw_text_rank]
	my_min=min(kw_text_rank_scores)
	my_max=max(kw_text_rank_scores)
	kw_text_rank=[[x[0],normalize(x[1],my_min,my_max)] for x in kw_text_rank]

	kw_text_rank=[x for x in kw_text_rank if x[1]>0.01]

	keywords=[]
	keywords.extend(kw_rake)
	keywords.extend(kw_text_rank)
	keywords=sorted(keywords, key=lambda x: x[1], reverse=True)

	final_keyword_list=[]
	for kw in keywords:

		if kw[0] not in [x[0] for x in final_keyword_list]:
			final_keyword_list.append(kw)

	keyword_entries=[x for x in final_keyword_list]
	keyword_frequency=[[x[0],x[1],len(re.findall(x[0],text.lower()))] for x in keyword_entries]
	my_min=min([x[2] for x in keyword_frequency])
	my_max=max([x[2] for x in keyword_frequency])
	keyword_frequency=[[x[0],x[1],normalize(x[2],my_min,my_max)] for x in keyword_frequency]
	keyword_frequency=[[x[0],x[1]] for x in keyword_frequency if x[2]>0.39]
	final_keyword_list=sorted(final_keyword_list, key=lambda x: x[1], reverse=True)
	#final ranked keyword list need to be saved in a json file as well
	return final_keyword_list

def main():
	text = "History and evolution of the arctic flora: in the footsteps of Eric. A major contribution to our initial understanding of the origin, history and biogeography of the present-day arctic flora was made by Eric Hulten in his landmark book Outline of the History of Arctic and Boreal Biota during the Quarternary Period, published in 1937. Here we review recent molecular and fossil evidence that has tested some of Hulten's proposals. There is now excellent fossil, molecular and phytogeographical evidence to support Hulten's proposal that Beringia was a major northern refugium for arctic plants throughout the Quaternary. In contrast, most molecular evidence fails to support his proposal that contemporary east and west Atlantic populations of circumarctic and amphi-Atlantic species have been separated throughout the Quaternary. In fact, populations of these species from opposite sides of the Atlantic are normally genetically very similar, thus the North Atlantic does not appear to have been a strong barrier to their dispersal during the Quaternary. Hulten made no detailed proposals on mechanisms of speciation in the Arctic; however, molecular studies have confirmed that many arctic plants are allopolyploid, and some of them most probably originated during the Holocene. Recurrent formation of polyploids from differentiated diploid or more low-ploid populations provides one explanation for the intriguing taxonomic complexity of the arctic flora, also noted by Hulten. In addition, population fragmentation during glacial periods may have lead to the formation of new sibling species at the diploid level. Despite the progress made since Hulten wrote his book, there remain large gaps in our knowledge of the history of the arctic flora, especially about the origins of the founding stocks of this flora which first appeared in the Arctic at the end of the Pliocene (approximately 3 Ma). Comprehensive analyses of the molecular phylogeography of arctic taxa and their relatives together with detailed fossil studies are required to fill these gaps. Quantification of population sizes of large herbivores and their long-term functional role in ecosystems using dung fungal spores. The relationship between large herbivore numbers and landscape cover over time is poorly understood. There are two schools of thought: one views large herbivores as relatively passive elements upon the landscape and the other as ecosystem engineers driving vegetation succession. The latter relationship has been used as an argument to support reintroductions of large herbivores onto many landscapes in order to increase vegetation heterogeneity and biodiversity through local-scale disturbance regimes. Most of the research examining the relationship between large herbivores and their impact on landscapes has used extant studies. An alternative approach is to estimate the impact of variations in herbivore populations through time using fossil dung fungal spores and pollen in sedimentary sequences. However, to date, there has been little quantification of fossil dung fungal spore records and their relationship to herbivore numbers, leaving this method open to varied interpretations. In this study, we developed further the dung fungal spore method and determined the relationship between spore abundance in sediments (number cm(-2)year(-1)) and herbivore biomass densities (kgha(-1)). To establish this relationship, we used the following: (i) the abundance of Sporormiella spp., Sordaria spp. and Podospora spp. spores in modern sediments from ponds and (ii) weekly counts of contemporary wildlife over a period of 5years from the rewilded site, Oostvaardersplassen, in the Netherlands. Results from this study demonstrate that there is a highly significant relationship between spore abundance and local biomass densities of herbivores that can be used in the calibration of fossil records. Mammal biomass density (comprising Konik horses, Heck cattle and red deer) predicts in a highly significant way the abundance of all dung fungal spores amalgamated together. This relationship is apparent at a very local scale (<10m), when the characteristics of the sampled ponds are taken into account (surface area of pond, length of shoreline). In addition, we identify that dung fungal spores are principally transported into ponds by surface run-off from the shores. These results indicate that this method provides a robust quantitative measure of herbivore population size over time. Herbivory Network: An international, collaborative effort to study herbivory in Arctic and alpine ecosystems. Plant-herbivore interactions are central to the functioning of tundra ecosystems, but their outcomes vary over space and time. Accurate forecasting of ecosystem responses to ongoing environmental changes requires a better understanding of the processes responsible for this heterogeneity. To effectively address this complexity at a global scale, coordinated research efforts, including multi-site comparisons within and across disciplines, are needed. The Herbivory Network was established as a forum for researchers from Arctic and alpine regions to collaboratively investigate the multifunctional role of herbivores in these changing ecosystems. One of the priorities is to integrate sites, methodologies, and metrics used in previous work, to develop a set of common protocols and design long-term geographically-balanced, coordinated experiments. The implementation of these collaborative research efforts will also improve our understanding of traditional human-managed systems that encompass significant portions of the sub-Arctic and alpine areas worldwide. A deeper understanding of the role of herbivory in these systems under ongoing environmental changes will guide appropriate adaptive strategies to preserve their natural values and related ecosystem services. (C) 2016 Elsevier B.V. and NIPR. All rights reserved. Biomass allometry for alder, dwarf birch, and willow in boreal forest and tundra ecosystems of far northeastern Siberia and north-central Alaska. Shrubs play an important ecological role in the Arctic system, and there is evidence from many Arctic regions of deciduous shrubs increasing in size and expanding into previously forb or graminoid-dominated ecosystems. There is thus a pressing need to accurately quantify regional and temporal variation in shrub biomass in Arctic regions, yet allometric equations needed for deriving biomass estimates from field surveys are rare. We developed 66 allometric equations relating basal diameter (BD) to various aboveground plant characteristics for three tall, deciduous shrub genera growing in boreal and tundra ecoregions in far northeastern Siberia (Yakutia) and north-central Alaska. We related BD to plant height and stem, branch, new growth (leaves + new twigs), and total aboveground biomass for alder (Alms viridis subsp. crispa and Alms fruticosa), dwarf birch (Betula nana subsp. exilis and divaricata), and willow (Salix spp.). The equations were based on measurements of 358 shrubs harvested at 33 sites. Plant height (r(2) = 0.48-0.95), total aboveground biomass (r(2) = 0.46-0.99), and component biomass (r(2) = 0.13-0.99) were significantly (P < 0.01) related to shrub BD. Alder and willow populations exhibited differences in allometric relationships across ecoregions, but this was not the case for dwarf birch. The allometric relationships we developed provide a tool for researchers and land managers seeking to better quantify and monitor the form and function of shrubs across the Arctic landscape. (C) 2014 Elsevier B.V. All rights reserved. Shrub expansion may reduce summer permafrost thaw in Siberian tundra. Climate change is expected to cause extensive vegetation changes in the Arctic: deciduous shrubs are already expanding, in response to climate warming. The results from transect studies suggest that increasing shrub cover will impact significantly on the surface energy balance. However, little is known about the direct effects of shrub cover on permafrost thaw during summer. We experimentally quantified the influence of Betula nana cover on permafrost thaw in a moist tundra site in northeast Siberia with continuous permafrost. We measured the thaw depth of the soil, also called the active layer thickness (ALT), ground heat flux and net radiation in 10 m diameter plots with natural B. nana cover (control plots) and in plots in which B. nana was removed (removal plots). Removal of B. nana increased ALT by 9% on average late in the growing season, compared with control plots. Differences in ALT correlated well with differences in ground heat flux between the control plots and B. nana removal plots. In the undisturbed control plots, we found an inverse correlation between B. nana cover and late growing season ALT. These results suggest that the expected expansion of deciduous shrubs in the Arctic region, triggered by climate warming, may reduce summer permafrost thaw. Increased shrub growth may thus partially offset further permafrost degradation by future temperature increases. Permafrost models need to include a dynamic vegetation component to accurately predict future permafrost thaw. Global assessment of nitrogen deposition effects on terrestrial plant diversity: a synthesis. Atmospheric nitrogen (N) deposition is it recognized threat to plant diversity ill temperate and northern parts of Europe and North America. This paper assesses evidence from field experiments for N deposition effects and thresholds for terrestrial plant diversity protection across a latitudinal range of main categories of ecosystems. from arctic and boreal systems to tropical forests. Current thinking on the mechanisms of N deposition effects on plant diversity, the global distribution of G200 ecoregions, and current and future (2030) estimates of atmospheric N-deposition rates are then used to identify the risks to plant diversity in all major ecosystem types now and in the future. This synthesis paper clearly shows that N accumulation is the main driver of changes to species composition across the whole range of different ecosystem types by driving the competitive interactions that lead to composition change and/or making conditions unfavorable for some species. Other effects such its direct toxicity of nitrogen gases and aerosols long-term negative effects of increased ammonium and ammonia availability, soil-mediated effects of acidification, and secondary stress and disturbance are more ecosystem, and site-specific and often play a supporting role. N deposition effects in mediterranean ecosystems have now been identified, leading to a first estimate of an effect threshold. Importantly, ecosystems thought of as not N limited, such as tropical and subtropical systems, may be more vulnerable in the regeneration phase. in situations where heterogeneity in N availability is reduced by atmospheric N deposition, on sandy soils, or in montane areas. Critical loads are effect thresholds for N deposition. and the critical load concept has helped European governments make progress toward reducing N loads on sensitive ecosystems. More needs to be done in Europe and North America. especially for the more sensitive ecosystem types. including several ecosystems of high conservation importance. The results of this assessment Show that the Vulnerable regions outside Europe and North America which have not received enough attention are ecoregions in eastern and Southern Asia (China, India), an important part of the mediterranean ecoregion (California, southern Europe). and in the coming decades several subtropical and tropical parts of Latin America and Africa. Reductions in plant diversity by increased atmospheric N deposition may be more widespread than first thought, and more targeted Studies are required in low background areas, especially in the G200 ecoregions. Meta-analysis of high-latitude nitrogen-addition and warming studies implies ecological mechanisms overlooked by land models. Accurate representation of ecosystem processes in land models is crucial for reducing predictive uncertainty in energy and greenhouse gas feedbacks with the climate. Here we describe an observational and modeling meta-analysis approach to benchmark land models, and apply the method to the land model CLM4.5 with two versions of belowground biogeochemistry. We focused our analysis on the aboveground and belowground responses to warming and nitrogen addition in high-latitude ecosystems, and identified absent or poorly parameterized mechanisms in CLM4.5. While the two model versions predicted similar soil carbon stock trajectories following both warming and nitrogen addition, other predicted variables (e.g., belowground respiration) differed from observations in both magnitude and direction, indicating that CLM4.5 has inadequate underlying mechanisms for representing high-latitude ecosystems. On the basis of observational synthesis, we attribute the model-observation differences to missing representations of microbial dynamics, aboveground and belowground coupling, and nutrient cycling, and we use the observational meta-analysis to discuss potential approaches to improving the current models. However, we also urge caution concerning the selection of data sets and experiments for meta-analysis. For example, the concentrations of nitrogen applied in the synthesized field experiments (average = 72 kg ha(-1) yr(-1)) are many times higher than projected soil nitrogen concentrations (from nitrogen deposition and release during mineralization), which precludes a rigorous evaluation of the model responses to likely nitrogen perturbations. Overall, we demonstrate that elucidating ecological mechanisms via meta-analysis can identify deficiencies in ecosystem models and empirical experiments."
	print((calculate_keywords(text)))

if __name__ == '__main__':
	main()