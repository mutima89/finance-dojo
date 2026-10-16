"""A light story thread: short notes from your (fictional) manager at the
fictional Aurelia Grand Hotel, one per module, so each topic has a reason."""
from __future__ import annotations

MANAGER = "Sofia Reyes"
MANAGER_ROLE = "General Manager, Aurelia Grand Hotel (fictional)"

# module number -> (subject line, message)
NOTES = {
    1: ("Welcome to the finance team!",
        "Glad you're here. Before anything fancy, I need you comfortable reading our P&L: where the money "
        "comes from, where it goes and what's left. Start with margins and you'll understand half of our "
        "Monday meeting."),
    2: ("Can you rebuild the weekly report?",
        "Our weekly revenue report lives in a messy spreadsheet that breaks every month. I'd love a clean "
        "version with clear inputs, formulas and checks. Show me you can build a model someone else can trust."),
    3: ("Rooms are our biggest lever",
        "Occupancy looks fine but RevPAR is behind plan. I want to understand why, and whether we should push "
        "rate or volume next season. Learn ADR, occupancy and RevPAR and then try the RM simulator."),
    4: ("Budget season is coming",
        "Next month we build the budget for next year. I need someone who can explain variances to department "
        "heads without making them defensive. Price, volume and mix will be your best friends."),
    5: ("What does next quarter look like?",
        "The owners want a forecast with a range, not a single magic number. Build me a simple driver-based "
        "forecast and tell me what would make it go better or worse. Nobody can promise the future, and "
        "that's fine."),
    6: ("Is this deal worth it?",
        "Sales wants to give a big corporate client a discount. Before I say yes, I need to know what it does "
        "to our margin and whether the volume makes up for it. Think like a commercial partner, not a gatekeeper."),
    7: ("Should we renovate the rooms?",
        "Renovating all 150 guest rooms costs a lot up front and pays back over years. Help me compare it with doing nothing "
        "using NPV, payback and a few what-ifs. I want a recommendation, with the risks spelled out."),
    8: ("Your first board pack",
        "You're ready to present. Pull the story together on one page: what happened, why, what's next and what "
        "we should do. Keep it short, clear and honest about uncertainty."),
}

CAPSTONE_NOTE = ("You made it!",
                 "You've worked through every module. The capstone is your chance to bring it all together on one "
                 "realistic case. Take your time, show your workings, and I'll be proud of whatever you send me.")

FOUR_QUESTIONS = ("What do the numbers tell me? Why did it happen? What might happen next? "
                  "What should management do?")


def note_for(module_number: int | None) -> tuple[str, str]:
    if module_number is None:
        return CAPSTONE_NOTE
    return NOTES.get(module_number, NOTES[1])
