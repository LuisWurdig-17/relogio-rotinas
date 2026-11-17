# -*- coding: utf-8 -*-
"""Relogio de disparo: espera ate o segundo certo e empurra o gatilho da rotina.

Por que existe: o agendador do GitHub atrasa horas. Aqui cada elo da corrente fica em espera pela regra de
espera do ambiente (nao ocupa maquina) ate uns 10 minutos antes do alvo, dorme os minutos finais e dispara
na hora. Depois agenda o elo seguinte. Sem dados de cliente: so horario e um empurrao num repositorio privado.

Alvos em UTC (Brasilia = UTC-3): 09:50 e 14:50, ou seja 6h50 e 11h50.
Corrente A dispara no alvo. Corrente B confere 4 minutos depois e so dispara se a A nao publicou.
"""
import os, sys, subprocess, time, datetime as dt, urllib.request

UTC = dt.timezone.utc
ALVOS = [(9, 50), (14, 50)]
ESPERAS = [1130, 600, 290, 120, 60, 30, 10, 1]
FOLGA = 10                      # o elo acorda pelo menos tantos minutos antes do alvo
PERTO = 25                      # com menos que isso, dorme na propria maquina e dispara
VERSAO = 'https://prumai.jcefin.com.br/pv3.txt'
CADEIA = os.environ.get('CADEIA', 'A')
MOTIVO = os.environ.get('MOTIVO', 'elo')
ALVO_IN = os.environ.get('ALVO', '').strip()
SIMULA = os.environ.get('SIMULA') == '1'
AGORA_FALSO = os.environ.get('AGORA')          # so para simulacao
ATRASO = 5 if CADEIA == 'A' else 240           # segundos depois do alvo

def agora():
    if SIMULA and AGORA_FALSO: return dt.datetime.fromisoformat(AGORA_FALSO).replace(tzinfo=UTC)
    return dt.datetime.now(UTC)
def diz(m): print(f'[{agora():%Y-%m-%d %H:%M:%S}Z {CADEIA}] {m}', flush=True)
def alvos(n):
    out = []
    for d in (-1, 0, 1, 2):
        b = (n + dt.timedelta(days=d)).replace(second=0, microsecond=0)
        out += [b.replace(hour=h, minute=m) for h, m in ALVOS]
    return sorted(out)
def proximo(depois_de): return min(a for a in alvos(depois_de) if a > depois_de)
def ultimo(ate): return max(a for a in alvos(ate) if a <= ate)
def escolhe_espera(minutos):
    cab = [e for e in ESPERAS if e <= minutos - FOLGA]
    return cab[0] if cab else 1

def roda(cmd, tentativas=3, pausa=20, **kw):
    for t in range(1, tentativas + 1):
        r = subprocess.run(cmd, capture_output=True, text=True, **kw)
        if r.returncode == 0: return True
        diz(f'  tentativa {t} falhou: {(r.stderr or r.stdout).strip()[-160:]}')
        if t < tentativas: time.sleep(pausa)
    return False

def empurra(texto):
    """Empurra uma linha nova em disparo.txt no ramo de gatilho do repositorio da rotina."""
    if SIMULA: diz(f'  (simulacao) empurraria o gatilho: {texto}'); return True
    casa = os.path.expanduser('~'); chave = os.path.join(casa, '.ssh', 'disparo')
    os.makedirs(os.path.dirname(chave), exist_ok=True)
    with open(chave, 'w') as f: f.write(os.environ['CHAVE_DISPARO'].strip() + '\n')
    os.chmod(chave, 0o600)
    amb = dict(os.environ, GIT_SSH_COMMAND=f'ssh -i {chave} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new')
    for t in range(1, 4):
        subprocess.run(['rm', '-rf', 'gatilho'])
        ok = subprocess.run(['git', 'clone', '-q', '--depth', '1', '--branch', 'disparo', os.environ['DESTINO'], 'gatilho'],
                            env=amb, capture_output=True, text=True).returncode == 0
        if ok:
            with open('gatilho/disparo.txt', 'w') as f: f.write(texto + '\n')
            cmds = [['git', '-C', 'gatilho', '-c', 'user.name=relogio', '-c', 'user.email=relogio@users.noreply.github.com',
                     'commit', '-q', '-am', 'disparo ' + texto[:60]], ['git', '-C', 'gatilho', 'push', '-q', 'origin', 'disparo']]
            ok = all(subprocess.run(c, env=amb, capture_output=True, text=True).returncode == 0 for c in cmds)
        if ok: diz(f'  gatilho empurrado: {texto}'); return True
        diz(f'  empurrao falhou (tentativa {t})'); time.sleep(15)
    return False

def agenda(alvo, motivo='elo'):
    """Dispara o proximo elo desta corrente, em espera ate perto do alvo."""
    minutos = (alvo - agora()).total_seconds() / 60
    esp = escolhe_espera(minutos)
    diz(f'  proximo elo: alvo {alvo:%d/%m %H:%M}Z, faltam {minutos:.0f} min, espera de {esp} min')
    if SIMULA: return True
    ok = roda(['gh', 'workflow', 'run', 'relogio.yml', '-f', f'cadeia={CADEIA}', '-f', f'espera=espera-{esp}',
               '-f', f'alvo={alvo:%Y-%m-%dT%H:%M}', '-f', f'motivo={motivo}'])
    if not ok:
        diz('  NAO consegui agendar o proximo elo; chamando a guarda')
        roda(['gh', 'workflow', 'run', 'guarda.yml'])
    return ok

def versao_no_ar():
    """Le o carimbo do painel no ar. Primeiro com curl (o mesmo caminho do vigia antigo), depois com a biblioteca."""
    url = VERSAO + '?' + str(int(time.time()))
    erro = ''
    for t in range(3):
        try:
            r = subprocess.run(['curl', '-s', '-f', '-m', '20', url], capture_output=True, text=True)
            num = ''.join(c for c in r.stdout if c.isdigit())[:14]
            if r.returncode == 0 and len(num) == 14: return dt.datetime.strptime(num, '%Y%m%d%H%M%S')
            erro = f'curl codigo {r.returncode}'
        except Exception as e: erro = str(e)[:80]
        try:
            with urllib.request.urlopen(url, timeout=15) as r:
                return dt.datetime.strptime(r.read().decode().strip()[:14], '%Y%m%d%H%M%S')
        except Exception as e: erro += ' | ' + str(e)[:80]
        if not SIMULA: time.sleep(5)
    diz(f'  nao li a versao no ar: {erro}'); return None
def publicado(alvo):
    v = versao_no_ar()
    return v is not None and v >= (alvo - dt.timedelta(hours=3)).replace(tzinfo=None)     # carimbo em hora de Brasilia

def dorme_ate(quando):
    while True:
        falta = (quando - agora()).total_seconds()
        if falta <= 0 or SIMULA: return
        time.sleep(min(falta, 30))

def registra(linha):
    if SIMULA or CADEIA != 'A': return
    os.makedirs('estado', exist_ok=True)
    with open('estado/disparos.log', 'a') as f: f.write(linha + '\n')
    cmds = [['git', 'add', 'estado/disparos.log'],
            ['git', '-c', 'user.name=relogio', '-c', 'user.email=relogio@users.noreply.github.com', 'commit', '-q', '-m', 'registro de disparo'],
            ['git', 'pull', '-q', '--rebase', '--autostash', 'origin', 'main'], ['git', 'push', '-q', 'origin', 'HEAD:main']]
    for c in cmds:
        if subprocess.run(c, capture_output=True, text=True).returncode != 0: diz('  registro nao gravado'); return

def main():
    n = agora(); falhou = False; atraso = 0
    alvo = dt.datetime.fromisoformat(ALVO_IN).replace(tzinfo=UTC) if ALVO_IN else None
    diz(f'elo iniciado: motivo {MOTIVO}, alvo recebido {alvo:%d/%m %H:%MZ}' if alvo else f'elo iniciado: motivo {MOTIVO}, sem alvo')
    if MOTIVO == 'inicio' or alvo is None:
        # corrente nova ou religada: se o ultimo alvo ficou sem versao, dispara ja; depois segue para o proximo
        u = ultimo(n)
        if not publicado(u): empurra(f'recuperacao do alvo {u:%d/%m %H:%M}Z, corrente {CADEIA}')
        agenda(proximo(n)); return 0
    falta = (alvo - n).total_seconds() / 60
    if falta > PERTO:                       # ainda longe: mais um elo de espera para o mesmo alvo
        agenda(alvo); return 0
    if falta < -1:                          # o elo acordou depois do alvo: dispara atrasado, agora
        atraso = -falta
        diz(f'  ATRASADO {-falta:.0f} min em relacao ao alvo')
    else:
        dorme_ate(alvo + dt.timedelta(seconds=ATRASO))
    if CADEIA == 'A' or not publicado(alvo):
        prefixo = 'forcar ensaio do ' if MOTIVO == 'ensaio' else ''      # ensaio: a rotina publica mesmo sem precisar
        if not empurra(f'{prefixo}alvo {alvo:%d/%m %H:%M}Z, corrente {CADEIA}, {agora():%H:%M:%S}Z'): falhou = True
    else:
        diz('  a outra corrente ja publicou; nada a empurrar')
    agenda(proximo(max(alvo, agora())))     # o elo seguinte fica garantido antes da conferencia
    # vigia: a versao no ar tem de passar do alvo; senao empurra de novo e, se nao resolver, a rodada falha
    for volta in (1, 2):
        dorme_ate(agora() + dt.timedelta(minutes=5))
        if SIMULA or publicado(alvo):
            registra(f'{agora():%Y-%m-%dT%H:%M:%SZ} alvo {alvo:%Y-%m-%dT%H:%M}Z publicado (conferencia {volta})' + (f', DISPARO ATRASADO {atraso:.0f} min' if atraso else ''))
            if atraso > 3 and not SIMULA:      # publicou, mas fora da hora: a rodada falha de proposito para o GitHub avisar por e-mail
                diz(f'::error::O painel foi publicado, mas o disparo saiu {atraso:.0f} min depois do alvo. Conferir as esperas do relogio.'); return 1
            return 0
        diz(f'  conferencia {volta}: o painel ainda nao tem versao do alvo; empurrando de novo')
        empurra(f'repeticao do alvo {alvo:%d/%m %H:%M}Z, corrente {CADEIA}')
    dorme_ate(agora() + dt.timedelta(minutes=5))
    if publicado(alvo):
        registra(f'{agora():%Y-%m-%dT%H:%M:%SZ} alvo {alvo:%Y-%m-%dT%H:%M}Z publicado (na repeticao)'); return 0
    registra(f'{agora():%Y-%m-%dT%H:%M:%SZ} alvo {alvo:%Y-%m-%dT%H:%M}Z NAO PUBLICADO')
    diz('::error::O painel nao foi publicado no alvo depois de 3 disparos. Conferir a rotina.')
    return 1

if __name__ == '__main__':
    sys.exit(main())
