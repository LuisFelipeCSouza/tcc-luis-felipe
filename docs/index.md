# Simulador e Analisador de Faltas em Redes de Distribuição

Bem-vindo à documentação oficial do framework de simulação de curto-circuito desenvolvido no âmbito do Trabalho de Conclusão de Curso (TCC) em Engenharia Elétrica na **Universidade Federal do Ceará (UFC)**.

Este projeto integra o poder computacional do **OpenDSS** com a flexibilidade do **Python** para criar um ambiente completo de análise de resiliência e proteção de sistemas elétricos.

---

## ⚡ Visão Geral do Sistema

O simulador foi projetado para pesquisadores e engenheiros que buscam automatizar a geração de dados de falta e validar algoritmos de localização. Ele opera sobre o modelo **IEEE 34 Barras**, permitindo uma análise granular de eventos de curto-circuito.

### O Fluxo de Trabalho (Pipeline)

A arquitetura do projeto é dividida em três pilares fundamentais, garantindo a integridade dos dados desde a simulação até a decisão final:

1. **Simulação Automatizada:** Geração de datasets massivos variando localização, tipo de falta e resistência ($R_f$).
2. **Localização via Mínima Reatância:** Implementação do algoritmo analítico para estimar a distância da falta baseada em medições de subestação.
3. **Filtragem por Smart Meters:** Uso de dados de medidores inteligentes para eliminar múltiplas estimativas e identificar o trecho exato do defeito.

---

## 🔬 Metodologia Científica

A base teórica deste projeto fundamenta-se na análise de componentes de sequência e no comportamento da reatância aparente vista pela proteção. O modelo computacional segue a relação:

$$V_{fault} = V_{prefault} - Z_{th} \cdot I_{fault}$$

Onde cada parâmetro é extraído dinamicamente da topologia da rede através da biblioteca **NetworkX**, permitindo que o algoritmo de localização seja agnóstico à complexidade do sistema.

---

## 🚀 Início Rápido

Para colocar o simulador em operação utilizando o gerenciador `uv`:

```bash
# Clone o repositório
git clone https://github.com/LuisFelipeCSouza/tcc-luis-felipe.git

# Instale as dependências e rode a simulação base
uv run automacao.py

```

> **Nota:** Este projeto utiliza o `py-dss-interface` para comunicação direta com a API COM do OpenDSS.

---

## 🎓 Como Citar

Se este software ou a metodologia aqui apresentada for útil para sua pesquisa acadêmica, por favor, utilize a seguinte referência:

```bibtex
@manual{souza2026tcc,
  title  = {Simulador e Analisador de Faltas em Redes de Distribuição Elétrica},
  author = {Souza, Luis Felipe Carneiro de},
  year   = {2026},
  note   = {Trabalho de Conclusão de Curso (Graduação em Engenharia Elétrica) - Universidade Federal do Ceará},
  url    = {https://github.com/LuisFelipeCSouza/tcc-luis-felipe}
}

```

---

## 🤝 Afiliação e Apoio

Desenvolvido no **Grupo de Redes Elétricas Inteligentes (GREI)**.

* **Departamento:** Engenharia Elétrica (DEE/UFC)
* **Localização:** Fortaleza, CE, Brasil