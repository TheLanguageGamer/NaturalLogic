import re

LEFT_TO_RIGHT = 0
RIGHT_TO_LEFT = 1

def string_to_bits(string, properties):
	ret = 0
	for part in string.split("|"):
		i = properties.index(part)
		ret += (1 << i)

	return ret

def bits_to_string(bits, properties):
	names = []
	for i in range(len(properties)):
		if bits & (1 << i):
			names.append(properties[i])
	return "|".join(names)

def is_variable(string):
	return string.startswith("_")

class GrammarRule(object):
	def __init__(self, lhs, rhs, drt, rem, add):
		self.lhs = lhs
		self.rhs = rhs
		self.drt = drt
		self.rem = rem
		self.add = add
		if self.drt == LEFT_TO_RIGHT:
			self.top = (self.rhs | self.add) & ~self.rem
		else:
			self.top = (self.lhs | self.add) & ~self.rem

	def to_string(self, properties):
		if self.drt == LEFT_TO_RIGHT:
			return "{} ==> {}-{}+{}, Top: {}, {} - {}".format(
				bits_to_string(self.lhs, properties),
				bits_to_string(self.rhs, properties),
				bits_to_string(self.rem, properties),
				bits_to_string(self.add, properties),
				bits_to_string(self.top, properties),
				self.lhs, self.rhs
			)
		else:
			return "{}-{}+{} <== {}, Top: {}, {} - {}".format(
				bits_to_string(self.lhs, properties),
				bits_to_string(self.rem, properties),
				bits_to_string(self.add, properties),
				bits_to_string(self.rhs, properties),
				bits_to_string(self.top, properties),
				self.lhs, self.rhs
			)

	def from_string(string, properties):
		m = re.search(r"^([A-Z|]+)\s*==>\s*([A-Z|]+)\-([A-Z|]+)\+([A-Z|]+)$", string)
		if m:
			return GrammarRule(
				string_to_bits(m.group(1), properties),
				string_to_bits(m.group(2), properties),
				LEFT_TO_RIGHT,
				string_to_bits(m.group(3), properties),
				string_to_bits(m.group(4), properties)
			)

		m = re.search(r"^([A-Z|]+)\-([A-Z|]+)\+([A-Z|]+)\s*<==\s*([A-Z|]+)$", string)
		if m:
			return GrammarRule(
				string_to_bits(m.group(1), properties),
				string_to_bits(m.group(4), properties),
				RIGHT_TO_LEFT,
				string_to_bits(m.group(2), properties),
				string_to_bits(m.group(3), properties)
			)
		assert(False)

class Node(object):
	def __init__(self, top, lhs, rhs):
		self.top = top
		self.lhs = lhs
		self.rhs = rhs

	def print(self, properties):
		print(bits_to_string(self.top, properties))
		if self.lhs != None and self.rhs != None:
			self.lhs.print(properties)
			self.rhs.print(properties)

	def to_qtree_latex(self, properties):
		return """[.{}
		{}
		{}
		]""".format(
			bits_to_string(self.top, properties),
			self.lhs.to_qtree_latex(properties),
			self.rhs.to_qtree_latex(properties)
		)

	def to_flat_text(self):
		return self.lhs.to_flat_text() + self.rhs.to_flat_text()

	def to_string(self, properties):
		return "{} [{} {}]".format(
			bits_to_string(self.top, properties),
			self.lhs.to_string(properties),
			self.rhs.to_string(properties)
		)

class Terminal(object):
	def __init__(self, top, token):
		self.top = top
		self.token = token

	def print(self, properties):
		print("{} -> {}".format(bits_to_string(self.top, properties), self.token))

	def __str__(self):
		return "{} -> {}".format(self.top, self.token)

	def __repr__(self):
		return "<Terminal: {} -> {}>".format(self.top, self.token)

	def to_qtree_latex(self, properties):
		return "[.{} {} ]".format(bits_to_string(self.top, properties), self.token)

	def to_flat_text(self):
		return self.token + " "

	def to_string(self, properties):
		return "{} {}".format(
			bits_to_string(self.top, properties),
			self.token
		)

class SubtreeVariable(object):
	def __init__(self, top, name):
		self.top = top
		self.name = name

	def print(self, properties):
		print("{} -> {}".format(bits_to_string(self.top, properties), self.name))

	def to_qtree_latex(self, properties):
		return "[.{} {} ]".format(bits_to_string(self.top, properties), self.name)

	def to_string(self, properties):
		return "{} {}".format(
			bits_to_string(self.top, properties),
			self.name
		)

class Grammar(object):

	def __init__(self, properties, rules, lexicon):
		self.properties = properties
		self.rules = rules
		self.lexicon = lexicon

	def from_data(properties, rules_data, lexicon_data):

		rules = []
		for string in rules_data:
			rule = GrammarRule.from_string(string, properties)
			rules.append(rule)

		lexicon = {key : string_to_bits(value, properties) for (key, value) in lexicon_data.items()}

		return Grammar(properties, rules, lexicon)

	def build_chart(self, tags):

		chart = [[[] for _ in range(len(tags))] for _ in range(len(tags))]
		for i in range(len(tags)):
			chart[i][i].append((tags[i], None, i))

		for width in range(1, len(tags)):
			for start in range(len(tags) - width):
				end = start + width
				for split in range(start, end):
					lhss = chart[start][split]
					rhss = chart[split+1][end]
					# print("Start: {}, Split: {}, End: {}, {} {}".format(start, split, end, lhss, rhss))
					for lhs in lhss:
						for rule in self.rules:
							if (lhs[0] | rule.lhs) == lhs[0]:
								for rhs in rhss:
									if (rhs[0] | rule.rhs) == rhs[0]:
										# print("Top: {}, LHS: {}, RHS: {}".format(rule.top, lhs, rhs))
										chart[start][end].append((rule.top, rule, split))

		return chart

	def chart_to_trees(self, chart, top, rule, start, split, end, tokens, i):
		if rule == None:
			trees = []
			if is_variable(tokens[i]):
				trees.append(SubtreeVariable(top, tokens[i]))
			else:
				trees.append(Terminal(top, tokens[i]))
			return (trees, i+1)
		trees = []
		lhss = chart[start][split]
		rhss = chart[split+1][end]
		for lhs in lhss:
			if (lhs[0] | rule.lhs) != lhs[0]:
				continue
			(lhs_trees, i) = self.chart_to_trees(
				chart,
				rule.lhs, #lhs[0] if lhs[1] != None else lhs[1].lhs,
				lhs[1],
				start,
				lhs[2],
				split,
				tokens,
				i
			)
			for rhs in rhss:
				if (rhs[0] | rule.rhs) == rhs[0]:
					(rhs_trees, i) = self.chart_to_trees(
						chart,
						rule.rhs, #rhs[0] if rhs[1] != None else rhs[1].rhs,
						rhs[1],
						split+1,
						rhs[2],
						end,
						tokens,
						i
					)
					for lhs_tree in lhs_trees:
						for rhs_tree in rhs_trees:
							trees.append(Node(top, lhs_tree, rhs_tree))
		return (trees, i)

	def parse(self, tokens):
		tags = [self.lexicon[token] for token in tokens]
		chart = self.build_chart(tags)
		trees = []
		for (bits, rule, split) in chart[0][len(tags)-1]:
			if bits == (1 << self.properties.index("S")):
				trees.extend(
					self.chart_to_trees(
						chart, bits, rule, 0, split, len(tags)-1, tokens, 0)[0])
		
		return trees

def tokenize(string):
	return string.split(" ")

properties = [
	"DET",
	"V",
	"N",
	"SING",
	"PLUR",
	"NP",
	"VP",
	"TR",
	"S",
]

rules_data = [
	"DET ==> N-N+NP",
	"NP ==> VP-VP+S",
	"TR-TR+VP <== NP",
]

lexicon_data = {
	"the" : "DET",
	"some" : "DET",
	"no" : "DET",
	"all" : "DET",
	"dog" : "N|SING",
	"dogs" : "NP|N|PLUR",
	"pets" : "NP|N|PLUR",
	"sweethearts" : "NP|N|PLUR",
	"food" : "N|NP",
	"eats" : "VP|TR",
	"are" : "TR|SING",
	"_W" : "NP|N|PLUR",
	"_X" : "NP|N|PLUR",
	"_Y" : "NP|N|PLUR",
	"_Z" : "NP|N|PLUR",
}

grammar = Grammar.from_data(properties, rules_data, lexicon_data)

def run_grammar_tests():
	tests = [
		("all dogs are pets", "S [NP [DET all N dogs] VP [TR are NP pets]]"),
		("the dogs are the pets", "S [NP [DET the N dogs] VP [TR are NP [DET the N pets]]]"),
		("the dog eats food", "S [NP [DET the N dog] VP [TR eats NP food]]"),
	]

	passed = 0
	for (string, parse_string) in tests:
		trees = grammar.parse(tokenize(string))
		if len(trees) == 0:
			print(f"Failed: Can't parse \"{string}\"")
		elif trees[0].to_string(properties) != parse_string:
			print(f"Failed: Incorrect parse for \"{string}\". Expected: \"{parse_string}\", got: \"{trees[0].to_string(properties)}\"")
		else:
			passed += 1
	print(f"{passed} / {len(tests)} grammar tests passed")

if __name__ == "__main__":
	run_grammar_tests()