# relogio-rotinas

Relógio de disparo de rotinas agendadas. Não tem dados: só horário.

O agendador do GitHub atrasa horas. Aqui cada rodada fica em espera pela regra de espera do ambiente
(`espera-N`, N minutos, sem ocupar máquina), acorda uns 10 minutos antes do alvo, dorme até o segundo
certo e empurra um gatilho num repositório privado, que roda a rotina na hora. Depois agenda a rodada
seguinte. Duas correntes independentes (A dispara no alvo; B confere 4 minutos depois e cobre) e uma
guarda que religa corrente parada.

Alvos: 09:50 e 14:50 UTC (6h50 e 11h50 de Brasília).
