import sys
from agent.orchestrator import Orchestrator


def main():
    print("\n🕹️  Welcome to the Agentic Game Builder!")
    print("   Describe your game idea and the agent will build it for you.\n")

    # Accept game idea from CLI argument or prompt interactively
    if len(sys.argv) > 1:
        game_idea = " ".join(sys.argv[1:])
        print(f"Game idea: {game_idea}\n")
    else:
        print("What kind of game do you want to build?")
        game_idea = input("You: ").strip()

        if not game_idea:
            print("No input provided. Please describe a game idea.")
            sys.exit(1)

    orchestrator = Orchestrator()
    success = orchestrator.run(game_idea)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()