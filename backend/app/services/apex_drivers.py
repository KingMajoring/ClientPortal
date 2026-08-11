"""WGTK's own driver roster, for picking a value to send to Apex's
PopulatePlannedDriver (a free-text field - Apex's GetDrivers method, which
would otherwise supply this list, isn't enabled on WGTK's Apex account).

Sourced from WGTK's "Drivers List" export out of Apex's own UI - there's no
API method to fetch this, so it's kept here as a static list rather than
built dynamically. Update this list by hand when drivers join/leave/change
vehicle - it's a rare enough event that a re-deploy is fine.
"""

DRIVERS = [
    {"buddy_no": "Mark N", "name": "Mark Neale"},
    {"buddy_no": "Blain H", "name": "Blain Harper"},
    {"buddy_no": "Charley J", "name": "Charley Jack"},
    {"buddy_no": "Chris W", "name": "Chris Webster"},
    {"buddy_no": "Connor T", "name": "Connor Todd"},
    {"buddy_no": "Dan W", "name": "Daniel White"},
    {"buddy_no": "Daryl B", "name": "Daryl Brandon"},
    {"buddy_no": "Dave C", "name": "Dave Chatten"},
    {"buddy_no": "Dean S", "name": "Dean Stewart"},
    {"buddy_no": "Jamie S", "name": "Jamie Steer"},
    {"buddy_no": "John Mas", "name": "John Mason"},
    {"buddy_no": "Josh S", "name": "Josh Sussex"},
    {"buddy_no": "Kev P", "name": "Kev Patterson"},
    {"buddy_no": "Lee D", "name": "Lee Denton"},
    {"buddy_no": "Liam S", "name": "Liam Smith"},
    {"buddy_no": "Lucy Ca", "name": "Lucy Cann"},
    {"buddy_no": "Michael M", "name": "Michael McCrossan"},
    {"buddy_no": "Pat S", "name": "Pat Smither"},
    {"buddy_no": "Peter N", "name": "Peter Newcomb"},
    {"buddy_no": "River D", "name": "River Dunn"},
    {"buddy_no": "Ross E", "name": "Ross Etchells"},
    {"buddy_no": "Ryan B", "name": "Ryan Bentley"},
    {"buddy_no": "Sean G", "name": "Sean Green"},
    {"buddy_no": "WGTK Panel", "name": "WGTK Panel"},
    {"buddy_no": "John P", "name": "John Poore"},
    {"buddy_no": "LOGS", "name": "WGTK LOGISTICS"},
    {"buddy_no": "Zak M", "name": "Zak Mathurin"},
    {"buddy_no": "Peter R", "name": "Peter Robertson"},
    {"buddy_no": "Ashley B", "name": "Ashley Bagshaw"},
    {"buddy_no": "Josh D", "name": "Josh D"},
    {"buddy_no": "Allan G", "name": "Allan Green"},
    {"buddy_no": "Mark B", "name": "Mark Butler"},
    {"buddy_no": "Lewis P", "name": "Lewis Parker"},
]
