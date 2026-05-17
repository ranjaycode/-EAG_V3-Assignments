"""
Built-in puzzle library for LogiSolve.
Each puzzle has a problem statement, category, difficulty, and known solution for verification.
"""

PUZZLES = {
    "einstein": {
        "name": "Einstein's Riddle",
        "category": "constraint_satisfaction",
        "difficulty": "hard",
        "problem": """
There are 5 houses in a row, each painted a different color.
Each house is occupied by a person of a different nationality.
Each person drinks a different beverage, smokes a different brand of cigarettes, and keeps a different pet.

Clues:
1.  The Brit lives in the red house.
2.  The Swede keeps dogs as pets.
3.  The Dane drinks tea.
4.  The green house is on the left of the white house.
5.  The green house owner drinks coffee.
6.  The person who smokes Pall Mall rears birds.
7.  The owner of the yellow house smokes Dunhill.
8.  The man living in the center house drinks milk.
9.  The Norwegian lives in the first house.
10. The man who smokes Blends lives next to the one who keeps cats.
11. The man who keeps horses lives next to the man who smokes Dunhill.
12. The owner who smokes BlueMaster drinks beer.
13. The German smokes Prince.
14. The Norwegian lives next to the blue house.
15. The man who smokes Blends has a neighbor who drinks water.

WHO OWNS THE FISH?
""",
        "answer": "The German (house 4) owns the fish.",
    },

    "scheduling": {
        "name": "Project Scheduling Problem",
        "category": "constraint_satisfaction",
        "difficulty": "medium",
        "problem": """
A software team must complete 6 tasks: A, B, C, D, E, F.

Constraints:
- Task B depends on Task A (B cannot start until A finishes).
- Task C depends on Task A.
- Task D depends on both B and C.
- Task E depends on Task C.
- Task F depends on both D and E.
- Task A takes 3 days, B takes 2 days, C takes 4 days, D takes 1 day, E takes 3 days, F takes 2 days.

Questions:
1. What is the critical path?
2. What is the minimum number of days to complete the project?
3. How much float does Task B have?
""",
        "answer": "Critical path: A→C→E→F (12 days). Task B has 2 days of float.",
    },

    "river_crossing": {
        "name": "River Crossing Puzzle",
        "category": "logic",
        "difficulty": "medium",
        "problem": """
A farmer needs to cross a river with a fox, a chicken, and a bag of grain.
The farmer has a small boat that can carry only himself and one other item at a time.

Constraints:
- If left alone, the fox will eat the chicken.
- If left alone, the chicken will eat the grain.
- The farmer must get all three across safely.

What is the minimum number of trips needed, and what is the exact sequence of moves?
""",
        "answer": "7 trips. Sequence: Take chicken → Return → Take fox → Return with chicken → Take grain → Return → Take chicken.",
    },

    "math_proof": {
        "name": "Number Theory: Divisibility Chain",
        "category": "arithmetic",
        "difficulty": "medium",
        "problem": """
Prove or disprove the following, showing all steps:

Given a positive integer N, define f(N) as follows:
- If N is even: f(N) = N / 2
- If N is odd:  f(N) = 3N + 1

Claim: Starting from N = 27, how many steps does it take before the sequence first reaches 1?
Show the first 10 values of the sequence and the total step count.

Also: What is the maximum value reached in the sequence before it descends to 1?
""",
        "answer": "111 steps. Maximum value: 9232. First 10 values: 27, 82, 41, 124, 62, 31, 94, 47, 142, 71.",
    },

    "knights_knaves": {
        "name": "Knights and Knaves",
        "category": "logic",
        "difficulty": "easy",
        "problem": """
On an island, Knights always tell the truth and Knaves always lie.

You meet three people: Alice, Bob, and Charlie.

Alice says: "All three of us are knaves."
Bob says: "Exactly one of us is a knight."
Charlie says: "Bob is a knave."

Determine whether each person is a Knight or a Knave. Show your full reasoning.
""",
        "answer": "Alice=Knave, Bob=Knight, Charlie=Knave. (Bob's statement is the only consistent one.)",
    },
}
