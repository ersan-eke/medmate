EMERGENCY = "This could be serious. Please call 999 now, or go to A&E. If you can, ask someone to stay with you."
NOT_COVERED = "I don't have that in my leaflets. Please ask your pharmacist."
# The similarity gate refuses before the model can tell off-topic from not covered, so one wording fits both.
GATE_REFUSAL = ("I can only answer questions about your medicines from my leaflets. For anything else about your health, "
                "please ask your pharmacist, or call NHS 111. In an emergency call 999.")
OFF_TOPIC = "I can only help with questions about your medicines. Please ask me about one of them."
FALLBACK = "I'm not sure. Please ask your pharmacist."
UNCONFIRMED_COMBINATION = "I can't confirm that combination from my leaflets. Please check with your pharmacist before taking them together."
INTERACTION_ADVICE = "Please check with your pharmacist before taking them together."
ALSO_TAKE = "You also take {}."  # leads the warnings for My medicines the question didn't name
NOT_HEARD = "Sorry, I didn't catch that. Please try again or type your question."
ATTRIBUTION = (
    "Information from the NHS website, licensed under the Open Government Licence v3.0. "
    "Not medical advice. In an emergency call 999."
)
