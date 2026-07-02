import json
with open('notebooks/01_credit_risk_eda_and_model.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'markdown' and '## Section 4 — ' in cell['source'][0]:
        nb['cells'][i]['source'] = [
            '## Section 4 — Risk Score Analysis: Defaulters vs Non-Defaulters\n',
            '\n',
            '**Business Question:** *How does the composite risk score distribute between defaulters and non-defaulters?*\n',
            '\n',
            'A boxplot allows us to visually assess the separation of the composite risk score between the two classes. Clear separation indicates that the risk score is a strong predictor of default.\n',
            '\n',
            'Key observations:\n',
            '- Defaulters generally have a higher composite risk score compared to non-defaulters.\n',
            '- The median risk score for defaulters is visibly separated from the median of repaid applicants.'
        ]
        
        nb['cells'][i+1]['source'] = [
            'plt.figure(figsize=(10, 6))\n',
            'sns.boxplot(data=df, x=\'label\', y=\'composite_risk_score\', \n',
            '            palette=[\'steelblue\', \'crimson\'], width=0.5)\n',
            '\n',
            'plt.xticks([0, 1], [\'Repaid (0)\', \'Defaulted (1)\'], fontsize=11)\n',
            'plt.xlabel(\'Loan Outcome\', fontsize=12)\n',
            'plt.ylabel(\'Composite Risk Score\', fontsize=12)\n',
            'plt.title(\'Distribution of Risk Score by Loan Outcome\', fontsize=14)\n',
            '\n',
            'plt.tight_layout()\n',
            'plt.savefig(\'../reports/risk_score_boxplot.png\', dpi=150, bbox_inches=\'tight\')\n',
            'plt.show()'
        ]
        break

with open('notebooks/01_credit_risk_eda_and_model.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)
