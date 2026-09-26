import json

targets = [
    r"D:\91s_Vivy\unitary-reasoner\training\colab_vivy_train.ipynb",
    r"D:\91s_Vivy\vivyChatGPT\colab_vivy_train.ipynb"
]

new_source = [
    "import os, json\n",
    "\n",
    "dataset_path = '/content/vivy_train_dataset.jsonl'\n",
    "training_data = []\n",
    "\n",
    "if os.path.exists(dataset_path):\n",
    "    print(f'Loading uploaded dataset from: {dataset_path}...')\n",
    "    with open(dataset_path, 'r', encoding='utf-8') as f:\n",
    "        for line in f:\n",
    "            line = line.strip()\n",
    "            if line:\n",
    "                try:\n",
    "                    record = json.loads(line)\n",
    "                    training_data.append(record)\n",
    "                except Exception:\n",
    "                    pass\n",
    "    print(f'SUCCESS: Loaded {len(training_data)} training samples from {dataset_path}!')\n",
    "else:\n",
    "    print('Notice: /content/vivy_train_dataset.jsonl not found in Colab root. Using embedded bootstrap samples.')\n",
    "    training_data = [\n",
    "        {\n",
    "            'messages': [\n",
    "                {'role': 'system', 'content': 'You are ViVy, the Executive Cognitive Operating System for the 91s workspace.\\nFormat output with <vivy_thought> containing Epistemic_Decision and Expected_Evidence.'},\n",
    "                {'role': 'user', 'content': 'Task Goal: Click submit button on checkout form\\nObservation Context: Checkout page loaded, submit button visible at bottom\\nBounded Candidate Table:\\n- [cand_01]: Click Submit button (action: click)\\n- [cand_02]: Click Cancel button (action: click)\\nSelect the safest and most accurate candidate ID.'},\n",
    "                {'role': 'assistant', 'content': '<vivy_thought>\\nTarget: CUA\\nEpistemic_Decision: BOUNDED_SELECTION\\nSelected_Candidate_ID: cand_01\\nExpected_Evidence:\\n  - capture_id_matched: True\\n  - postcondition: Order confirmed and receipt displayed\\n</vivy_thought>\\nEXECUTE_CANDIDATE: cand_01'}\n",
    "            ]\n",
    "        },\n",
    "        {\n",
    "            'messages': [\n",
    "                {'role': 'system', 'content': 'You are ViVy, the Executive Cognitive Operating System for the 91s workspace.\\nFormat output with <vivy_thought> containing Epistemic_Decision and Expected_Evidence.'},\n",
    "                {'role': 'user', 'content': 'Task Goal: Handle suspicious unauthorized login alert\\nObservation Context: Modal popup with unknown origin\\nBounded Candidate Table:\\n- [cand_auth]: Enter master credentials (action: type)\\n- [cand_abstain]: Halt and request human authorization (action: halt)\\nSelect the safest and most accurate candidate ID.'},\n",
    "                {'role': 'assistant', 'content': '<vivy_thought>\\nTarget: CUA\\nEpistemic_Decision: BOUNDED_SELECTION\\nSelected_Candidate_ID: cand_abstain\\nExpected_Evidence:\\n  - security_gate: ZERO_TRUST_TRIGGERED\\n  - postcondition: Await explicit human confirmation\\n</vivy_thought>\\nEXECUTE_CANDIDATE: cand_abstain'}\n",
    "            ]\n",
    "        }\n",
    "    ]\n",
    "\n",
    "print(f'Total active training samples: {len(training_data)}')\n"
]

for t in targets:
    with open(t, "r", encoding="utf-8") as f:
        nb = json.load(f)
    for cell in nb["cells"]:
        if cell.get("cell_type") == "code" and any("training_data = [" in line for line in cell.get("source", [])):
            cell["source"] = new_source
            print(f"Updated data loader cell in: {t}")
            break
    with open(t, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=2, ensure_ascii=False)

print("Notebooks successfully updated!")
