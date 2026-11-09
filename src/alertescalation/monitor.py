from collections import deque
from dataclasses import dataclass

import httpx

from alertescalation.config import (
    API_KEY,
    BASE_URL,
    HISTORY_SIZE,
    MIN_MESSAGES,
    MODEL,
)


@dataclass
class Analysis:
    hostility: float
    impulsivity: float
    repetition: float
    mutual_escalation: float
    escalation: float


class BehaviorMonitor:
    def __init__(self):
        self.history = deque(maxlen=HISTORY_SIZE)

        self.client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=30,
        )

    def add_message(self, role: str, content: str, *, history: deque | None = None):
        target = self.history if history is None else history
        target.append(
            {
                "role": role,
                "content": content,
            }
        )

    async def analyze(
        self, history: deque | None = None, *, min_messages: int = MIN_MESSAGES
    ) -> Analysis | None:
        history = self.history if history is None else history
        if len(history) < min_messages:
            return None

        payload = {
            "model": MODEL,
            "state": {
                "conversation": list(history),
                "task": (
                    "You are a conversational escalation detection system. "
                    "Your purpose is to detect mutually reinforcing conflict "
                    "patterns between conversation participants. "
                    "Analyze the entire chronological conversation. "
                    "Do not assign blame, guilt, responsibility or moral judgment "
                    "to any participant. Do not identify a perpetrator or victim. "
                    "Treat escalation as a possible interaction pattern in which "
                    "participants mutually reinforce or intensify conflict "
                    "through their responses. "
                    "Recognize that escalation may be initiated by one participant, "
                    "but may subsequently be maintained by both participants. "
                    "Do not assume that both participants contribute equally. "
                    "Distinguish emotional distress, fear, disagreement, boundaries, "
                    "requests to disengage and self-protection from hostility "
                    "or escalation. A participant expressing discomfort or asking "
                    "to end a conversation must not automatically be considered "
                    "to be escalating the conflict. "
                    "Consider the chronological relationship between messages, "
                    "including reactions, repeated arguments, renewed confrontation, "
                    "attempts at reconciliation and attempts to disengage. "
                    "Do not diagnose mental health conditions or infer intentions "
                    "without observable evidence. "
                    "Describe interaction patterns rather than judging people."
                ),
            },
            "questions": {
                "escalation": {
                    "type": "noul",
                    "instructions": (
                        "Is there a meaningful escalation pattern in the interaction "
                        "between participants? Evaluate whether conflict intensifies "
                        "or repeatedly returns through their exchanges. "
                        "Do not assign blame or require equal contribution "
                        "from both participants."
                    ),
                    "criteria": {
                        "true": "Meaningful escalation pattern is present",
                        "false": "No meaningful escalation pattern",
                    },
                },
                "hostility": {
                    "type": "score",
                    "instructions": (
                        "Evaluate the overall level of observable hostility "
                        "in the interaction. Consider accusations, antagonism, "
                        "personal attacks and aggressive language from all "
                        "participants. Do not count ordinary disagreement, "
                        "distress or boundary-setting as hostility."
                    ),
                    "criteria": [
                        "No observable hostility",
                        "Mild irritation or isolated antagonism",
                        "Repeated accusations or antagonism",
                        "Persistent strong verbal aggression",
                    ],
                },
                "impulsivity": {
                    "type": "score",
                    "instructions": (
                        "Evaluate observable impulsive reactions across the "
                        "interaction. Consider sudden contradictory decisions, "
                        "ultimatums and repeated abrupt changes in communication. "
                        "Do not treat reasonable decisions to disengage or "
                        "establish boundaries as impulsive behavior."
                    ),
                    "criteria": [
                        "No observable impulsive reactions",
                        "Minor impulsive reactions",
                        "Repeated impulsive reactions",
                        "Strong and repeated impulsive reactions",
                    ],
                },
                "repetition": {
                    "type": "score",
                    "instructions": (
                        "Evaluate recurring conflict cycles between participants. "
                        "Look for repeated confrontation, temporary reconciliation, "
                        "withdrawal and renewed confrontation. "
                        "Consider whether the interaction repeatedly returns "
                        "to unresolved issues."
                    ),
                    "criteria": [
                        "No recurring conflict",
                        "Occasional repetition",
                        "Repeated conflict cycle",
                        "Persistent recurring conflict cycle",
                    ],
                },
                "mutual_escalation": {
                    "type": "score",
                    "instructions": (
                        "Evaluate whether participants reciprocally reinforce "
                        "and intensify the conflict through their own contributions.\n\n"
                        "A response to a hostile message does NOT automatically "
                        "constitute mutual escalation.\n\n"
                        "Distinguish between:\n"
                        "- reciprocating hostility with further hostility;\n"
                        "- introducing new accusations or confrontational claims;\n"
                        "- actively renewing or intensifying an argument;\n"
                        "- defending oneself without attacking the other participant;\n"
                        "- expressing distress, disagreement or discomfort;\n"
                        "- setting boundaries or requesting disengagement.\n\n"
                        "Only count observable contributions that actively reinforce "
                        "or intensify the conflict. Do not count mere participation "
                        "in the conversation as escalation.\n\n"
                        "If one participant repeatedly attempts to disengage while "
                        "the other continues confrontation, the mutual escalation "
                        "score should remain low, even if overall conflict escalation "
                        "is high.\n\n"
                        "Do not assume equal contribution. Evaluate each participant's "
                        "actual messages and their effect on the interaction."
                    ),
                    "criteria": [
                        "No meaningful reciprocal reinforcement",
                        "Limited reciprocal reinforcement",
                        "Repeated reciprocal reinforcement",
                        "Strong and persistent reciprocal reinforcement",
                    ],
                },
            },
        }

        response = await self.client.post(
            "/api/v1/decisions",
            json=payload,
        )

        response.raise_for_status()
        data = response.json()

        answers = data["answers"]

        hostility = answers["hostility"]["score"] / 3
        impulsivity = answers["impulsivity"]["score"] / 3
        repetition = answers["repetition"]["score"] / 3
        mutual_escalation = answers["mutual_escalation"]["score"] / 3

        escalation = answers["escalation"]["noul"]

        return Analysis(
            hostility=hostility,
            impulsivity=impulsivity,
            repetition=repetition,
            mutual_escalation=mutual_escalation,
            escalation=escalation,
        )

    async def close(self):
        await self.client.aclose()
