import re
import subprocess
import itertools

from grammar import grammar, tokenize, SubtreeVariable, Terminal, Node

# Latex helper functions:

def wrap_latex(content):

	tex = r"""\documentclass{article}

\usepackage{amssymb}
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{stmaryrd}
\usepackage{qtree}

\begin{document}

	"""
	tex += content
	tex += "\n\n" + r"\end{document}"
	return tex

def latex_to_pdf(tex, filename="output"):
	open(f"output/{filename}.tex", "wt").write(tex)

	subprocess.call(
		["pdflatex", "-output-directory=output", f"output/{filename}.tex"],
		stdout = subprocess.DEVNULL,
		stderr = subprocess.STDOUT
	)

def trees_to_latex(trees):

	tex = ""
	for tree in trees:
		tex += r"\Tree" + tree.to_qtree_latex(properties)

	tex = wrap_latex(tex)
	latex_to_pdf(tex, filename)

def proof_to_latex(premises, steps, checks):

	tex = r"\begin{enumerate}"

	for premise in premises:
		tex += r"\item " + premise.to_flat_text() + ", premise\n"

	assert len(steps) == len(checks), "proof length should be same as checks length"

	for i in range(len(steps)):
		step = steps[i]
		check = checks[i]
		tex += r"\item " + step.to_flat_text().strip() + ", " + ", ".join(str(j+1) for j in check[0]) + " " + check[1].name

	tex += "\n\n" + r"\end{enumerate}"

	return tex

# Natural logic

class ProofRule(object):
	
	def __init__(self, forms_in, forms_out, name):
		self.forms_in = forms_in
		self.forms_out = forms_out
		self.name = name

	def from_pseudo_parse(forms_in_data, forms_out_data, name):
		return ProofRule(
			[sentence_form_parser(form) for form in forms_in_data],
			[sentence_form_parser(form) for form in forms_out_data],
			name
		)

	def from_strings(grammar, forms_in_strings, forms_out_strings, name):
		return ProofRule(
			[tree for string in forms_in_strings for tree in grammar.parse(tokenize(string))],
			[tree for string in forms_out_strings for tree in grammar.parse(tokenize(string))],
			name
		)

	def to_latex(self, properties):

		tex = self.name + "\n\n"
		tex += "Match: \n\n"
		for tree in self.forms_in:
			tex += r"\Tree" + tree.to_qtree_latex(properties)
		tex += "\n\nGenerate: \n\n"
		for tree in self.forms_out:
			tex += r"\Tree" + tree.to_qtree_latex(properties)
		
		return tex

	def __repr__(self):
		return "<ProofRule: \"{}\">".format(self.name)

INVALID_PROOF_RULE = ProofRule([], [], "Could not infer this step")

def proof_checker(proof_rules, premises, steps):
	have = [premise for premise in premises]
	checks = []

	for check_index in range(len(steps)):
		step = steps[check_index]
		candidates = []
		for rule in proof_rules:
			for form_out in rule.forms_out:
				assignment = match(form_out, step, {})
				if assignment != None:
					candidates.append((rule, assignment))

		check = None
		for (rule, out_assignment) in candidates:
			if check != None:
				break
			n = len(rule.forms_in)
			for stuff1 in itertools.combinations(range(len(have)), n):
				if check != None:
					break
				for stuff2 in itertools.permutations(stuff1):
					if check != None:
						break
					in_assignment = {}
					for j in range(n):
						in_assignment = match(rule.forms_in[j], have[stuff2[j]], in_assignment)
						if in_assignment == None:
							break
					if in_assignment != None:
						is_match = None
						for (variable, value) in out_assignment.items():
							is_match = match(value, in_assignment[variable], {})
							if is_match == None:
								break
						if is_match != None:
							check = (stuff2, rule)

		if check != None:
			have.append(step)
			checks.append(check)
		else:
			checks.append(([], INVALID_PROOF_RULE))

	return checks


def sentence_form_parser(form_data):
	if len(form_data) == 3 and type(form_data[0]) == str and type(form_data[1]) == list and type(form_data[2]) == list:
		return Node(
			string_to_bits(form_data[0], properties),
			sentence_form_parser(form_data[1]),
			sentence_form_parser(form_data[2])
		)
	elif len(form_data) == 2 and type(form_data[0]) == str and type(form_data[1]) == str:
		assert len(form_data[1]), "must have non-zero length"
		if form_data[1][0] == "_":
			return SubtreeVariable(
				string_to_bits(form_data[0], properties),
				form_data[1]
			)
		else:
			return Terminal(
				string_to_bits(form_data[0], properties),
				form_data[1]
			)
	else:
		assert False, "invalid proof form_data: {}".format(form_data)

def match(form, phrase, assignment):
	# TODO: Reevaluate this check. Without it, syntactic categories are ignored when matching sentence forms to sentences.
	# Indeed, in Moss's logics, different occurances of a variable have different syntactic categories, but can we ignore
	# syntactic category in general?
	# if (form.top | phrase.top) != phrase.top:
	# 	print("non-match, {} vs {}, [{}] vs [{}]".format(
	# 		bits_to_string(form.top, properties),
	# 		bits_to_string(phrase.top, properties),
	# 		form.to_string(properties),
	# 		phrase.to_string(properties)

	# 	))
	# 	return None
	if type(form) == Terminal:
		if type(phrase) != Terminal or form.token != phrase.token:
			return None
		return assignment
	elif type(form) == SubtreeVariable:
		if (form.name in assignment) and match(assignment[form.name], phrase, {}) != {}:
			return None
		assignment[form.name] = phrase
		return assignment
	elif type(form) == Node and type(phrase) == Node:
		assignment = match(form.lhs, phrase.lhs, assignment)
		if assignment == None:
			return None
		assignment = match(form.rhs, phrase.rhs, assignment)
		return assignment
	return None

def generate(form, assignment):
	if type(form) == Node:
		return Node(
			form.top,
			generate(form.lhs, assignment),
			generate(form.rhs, assignment)
		)
	elif type(form) == Terminal:
		return form
	elif type(form) == SubtreeVariable:
		assert form.name in assignment, "Variable '{}' not in assignment".format(form.name)
		return assignment[form.name]

# Implementation

transitivity_of_all = ProofRule.from_strings(
	grammar,
	[
		"all _X are _Y",
		"all _Y are _Z",
	],
	[
		"all _X are _Z",
	],
	"transitivity of all"
)

symmetric_all = ProofRule.from_strings(
	grammar,
	[],
	[
		"all _X are _X",
	],
	"symmetric all"
)

reflexivity_of_some = ProofRule.from_strings(
	grammar,
	[
		"some _X are _Y",
	],
	[
		"some _Y are _X",
	],
	"reflexivity of some"
)

conditional_symmetric_some = ProofRule.from_strings(
	grammar,
	[
		"some _X are _Y",
	],
	[
		"some _X are _X",
	],
	"conditional symmetric some"
)

application_of_all_to_some = ProofRule.from_strings(
	grammar,
	[
		"all _X are _Y",
		"some _Z are _X",
	],
	[
		"some _Z are _Y",
	],
	"application of all to some"
)

reflexivity_of_no = ProofRule.from_strings(
	grammar,
	[
		"no _X are _Y",
	],
	[
		"no _Y are _X",
	],
	"reflexivity of no"
)

application_of_all_to_no = ProofRule.from_strings(
	grammar,
	[
		"all _X are _Y",
		"no _Y are _Z",
	],
	[
		"no _X are _Z",
	],
	"application of all to no"
)

none_implies_none_are_anything = ProofRule.from_strings(
	grammar,
	[
		"no _X are _X",
	],
	[
		"no _X are _Y",
	],
	"none implies none are anything"
)

none_implies_all_are_anything = ProofRule.from_strings(
	grammar,
	[
		"no _X are _X",
	],
	[
		"all _X are _Y",
	],
	"none implies all are anything"
)

logic_of_all_and_some = [
	transitivity_of_all,
	symmetric_all,
	
	reflexivity_of_some,
	conditional_symmetric_some,
	application_of_all_to_some,
]

logic_of_all_some_and_no = [
	transitivity_of_all,
	symmetric_all,
	
	reflexivity_of_some,
	conditional_symmetric_some,
	application_of_all_to_some,
	
	reflexivity_of_no,
	application_of_all_to_no,
	none_implies_none_are_anything,
	none_implies_all_are_anything,
]

def run_logic_tests():
	tests = [
		{
			"logic" : logic_of_all_and_some,
			"premises" : [
				"all dogs are pets",
				"some dogs are dogs",
				"all dogs are sweethearts",
			],
			"steps" : [
				"some dogs are pets",
				"some pets are dogs",
				"some pets are sweethearts",
			],
			"expected" : '[((0, 1), <ProofRule: "application of all to some">), ((3,), <ProofRule: "reflexivity of some">), ((2, 4), <ProofRule: "application of all to some">)]'
		}
	]

	passed = 0
	for test in tests:
		checks = proof_checker(
			test["logic"],
			[grammar.parse(tokenize(premise))[0] for premise in test["premises"]],
			[grammar.parse(tokenize(step))[0] for step in test["steps"]],
		)
		if str(checks) != test["expected"]:
			print(f"""Failed. Expected: {test["expected"]}
Got: {str(checks)}
""")
		else:
			passed += 1
	print(f"{passed} / {len(tests)} logic tests passed")

if __name__ == "__main__":
	run_logic_tests()














