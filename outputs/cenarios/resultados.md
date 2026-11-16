# Resultados dos cenários (gerados pela execução da rede)

## S1_preditivo_ingresso (preditiva)
**Pergunta:** Como o perfil de ingresso, sem nenhuma informação de desempenho, altera a distribuição do desfecho?

- **perfil_risco** — Noturno, maduro, sem bolsa, nota de admissão baixa  
  Evidências: `{'Turno': 'Noturno', 'Faixa_Etaria': 'Maduro', 'Bolsista': 'Nao', 'Nota_Admissao': 'Baixa'}`
  - P(Desfecho): Dropout=0.504, Enrolled=0.142, Graduate=0.353
- **perfil_protegido** — Diurno, jovem, bolsista, nota de admissão alta  
  Evidências: `{'Turno': 'Diurno', 'Faixa_Etaria': 'Jovem', 'Bolsista': 'Sim', 'Nota_Admissao': 'Alta'}`
  - P(Desfecho): Dropout=0.271, Enrolled=0.151, Graduate=0.578

Expectativas qualitativas:
- [OK] P(Desfecho=Dropout): perfil_risco (0.504) > perfil_protegido (0.271)
- [OK] P(Desfecho=Graduate): perfil_protegido (0.578) > perfil_risco (0.353)

## S2_alerta_precoce (preditiva)
**Pergunta:** Quanto o desempenho no 1º semestre altera o risco de evasão de um mesmo perfil de ingresso?

- **sem1_baixo** — Desempenho baixo no 1º semestre  
  Evidências: `{'Faixa_Etaria': 'Maduro', 'Turno': 'Noturno', 'Bolsista': 'Nao', 'Desempenho_Sem1': 'Baixo'}`
  - P(Desfecho): Dropout=0.587, Enrolled=0.139, Graduate=0.274
  - P(Desempenho_Sem2): Baixo=0.714, Medio=0.174, Alto=0.113
- **sem1_alto** — Desempenho alto no 1º semestre  
  Evidências: `{'Faixa_Etaria': 'Maduro', 'Turno': 'Noturno', 'Bolsista': 'Nao', 'Desempenho_Sem1': 'Alto'}`
  - P(Desfecho): Dropout=0.314, Enrolled=0.149, Graduate=0.537
  - P(Desempenho_Sem2): Baixo=0.176, Medio=0.203, Alto=0.622

Expectativas qualitativas:
- [OK] P(Desfecho=Dropout): sem1_baixo (0.587) > sem1_alto (0.314)
- [OK] P(Desempenho_Sem2=Baixo): sem1_baixo (0.714) > sem1_alto (0.176)

## S3_diagnostico (diagnostica)
**Pergunta:** Sabendo que o estudante evadiu, quais condições ficam mais prováveis?

- **prior** — Sem evidência (distribuição a priori)  
  Evidências: `nenhuma (a priori)`
  - P(Pressao_Financeira): Baixa=0.557, Alta=0.443
  - P(Desempenho_Sem2): Baixo=0.339, Medio=0.194, Alto=0.467
  - P(Devedor): Sim=0.091, Nao=0.909
  - P(Mensalidade_Em_Dia): Sim=0.909, Nao=0.091
- **dropout** — Desfecho = Dropout  
  Evidências: `{'Desfecho': 'Dropout'}`
  - P(Pressao_Financeira): Baixa=0.387, Alta=0.613
  - P(Desempenho_Sem2): Baixo=0.619, Medio=0.199, Alto=0.182
  - P(Devedor): Sim=0.118, Nao=0.882
  - P(Mensalidade_Em_Dia): Sim=0.882, Nao=0.118

Expectativas qualitativas:
- [OK] P(Pressao_Financeira=Alta): dropout (0.613) > prior (0.443)
- [OK] P(Desempenho_Sem2=Baixo): dropout (0.619) > prior (0.339)
- [OK] P(Devedor=Sim): dropout (0.118) > prior (0.091)
- [OK] P(Mensalidade_Em_Dia=Nao): dropout (0.118) > prior (0.091)

## S4_prescritivo (prescritiva)
**Pergunta:** Para um perfil de risco, vale a pena conceder bolsa, considerando probabilidades, utilidades e custo?

- **bolsa_sim** — Com bolsa  
  Evidências: `{'Faixa_Etaria': 'Maduro', 'Turno': 'Noturno', 'Nota_Admissao': 'Baixa', 'Escolaridade_Pais': 'Baixa', 'Deslocado': 'Sim', 'Desemprego': 'Alto', 'Bolsista': 'Sim'}`
  - P(Desfecho): Dropout=0.516, Enrolled=0.142, Graduate=0.343
- **bolsa_nao** — Sem bolsa  
  Evidências: `{'Faixa_Etaria': 'Maduro', 'Turno': 'Noturno', 'Nota_Admissao': 'Baixa', 'Escolaridade_Pais': 'Baixa', 'Deslocado': 'Sim', 'Desemprego': 'Alto', 'Bolsista': 'Nao'}`
  - P(Desfecho): Dropout=0.584, Enrolled=0.139, Graduate=0.277

Expectativas qualitativas:
- [OK] P(Desfecho=Dropout): bolsa_nao (0.584) > bolsa_sim (0.516)

Decisão (utilidade esperada líquida):
- bolsa_sim: EU = -29.49 (custo 15)
- bolsa_nao: EU = -27.97 (custo 0)
- **Melhor alternativa:** bolsa_nao
- Custo de equilíbrio de `bolsa_sim` frente a `bolsa_nao`: 13.48 (acima disso a recomendação se inverte)
