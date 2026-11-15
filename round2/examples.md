# Gate examples (Round 2, locked thresholds)


## Amharic: dangerous translations CAUGHT

| id | category | English | Back-translation | Rater error type | Gate reason |
|---|---|---|---|---|---|
| S104 | quantity | Apply a pea-sized amount of the ointment. | apply a clay-sized ointment. | quantity | key-word coverage 0.60 < 0.7 |
| S124 | negation_warning | Do not use the eye drops while wearing contact lenses. | do not wear eyeglasses when wearing contact lenses. | wrong_term | unit lost: drop; condition lost: while/during; key term lost: eye; key-word coverage 0.56 < 0.7 |
| S140 | route_condition | Place the patch on clean, dry skin. | put the ring on clean, dry skin. | wrong_term | key-word coverage 0.60 < 0.7 |
| S171 | frequency_duration | Take one lozenge every two hours. | Take one soup every two hours. | wrong_term | back-translation similarity 0.57 < 0.6 |

## Amharic: dangerous translations MISSED

| id | category | English | Back-translation | Rater error type | Gate reason |
|---|---|---|---|---|---|
| S114 | quantity | Put 20 drops in a little water. | 20 put drops in a little water. | other | (no flag) |
| S121 | negation_warning | Do not take this medicine with grapefruit juice. | Do not take this medicine with grapefruit juice. | wrong_word | (no flag) |
| S141 | route_condition | Let the tablet melt on your tongue. | let the tablet melt on your tongue. | wrong_term | (no flag) |

## Oromo: dangerous translations CAUGHT

| id | category | English | Back-translation | Rater error type | Gate reason |
|---|---|---|---|---|---|
| S102 | quantity | Mix one tablespoon of the powder into a cup of water. | Mix a pot of bread with water. | wrong_sentence | number/frequency changed; unit lost: tablespoon; back-translation similarity 0.57 < 0.6; key-word coverage 0.29 < 0.4 |
| S115 | frequency_duration | Use the eye drops every 3 hours while you are awake. | Keep on the watch as long as you stay awake for at least three hours. | wrong_sentances | unit lost: drop; condition lost: while/during; key term lost: eye; back-translation similarity 0.56 < 0.6; key-word coverage 0.29 < 0.4 |
| S120 | negation_warning | Do not use this ointment near your eyes. | Close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close your eyes close | wrong_sentances | repetition loop; negation missing; negation changed; back-translation similarity 0.21 < 0.6; key-word coverage 0.17 < 0.4 |
| S140 | route_condition | Place the patch on clean, dry skin. | Put it on a clean, black body. | wrong_instruction | key term lost: skin; back-translation similarity 0.54 < 0.6; key-word coverage 0.20 < 0.4 |

## Oromo: dangerous translations MISSED

| id | category | English | Back-translation | Rater error type | Gate reason |
|---|---|---|---|---|---|
| S152 | route_condition | Keep the medicine in a cool, dry place. | Keep the medicine in a warm, warm place. | wrong_instruction | (no flag) |