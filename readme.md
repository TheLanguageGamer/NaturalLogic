Just some scraps for thinking through what's going on in Larry Moss's Natural Logic.

Specify proof rules:
```python
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

logic_of_all_and_some = [
	transitivity_of_all,
	symmetric_all,
	
	reflexivity_of_some,
	conditional_symmetric_some,
	application_of_all_to_some,
]
```

Specify and check a proof:
```python
proof = {
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
}

checks = proof_checker(
    proof["logic"],
    [grammar.parse(tokenize(premise))[0] for premise in proof["premises"]],
    [grammar.parse(tokenize(step))[0] for step in proof["steps"]],
)
```

Output result of proof checker to PDF:
```python
latex_to_pdf(wrap_latex(proof_to_latex(proof["premises"], proof["steps"], checks)))
```

