import time
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

TELEGRAM_TOKEN = "8725940003:AAHRHvUYcVQ6fW2_6pbB0QJxTvJOCnXZQYg"
CHAT_ID = "1099565196"

# Estrutura do histórico:
# { event_id: {"score": "0-0", "chances_no_placar": 0, "last_total_chances": 0, "notificado": False} }
historico_jogos = {}

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload, timeout=5)
    except Exception as e:
        print(f"Erro Telegram: {e}")

def obter_jogos_sofascore():
    url = "https://api.sofascore.com/api/v1/sport/football/events/live"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        data = res.json()
        return data.get("events", [])
    except Exception as e:
        print(f"Erro ao buscar jogos ao vivo: {e}")
        return []

def checar_big_chances_e_placar(event_id, home_team, away_team, current_home_score, current_away_score):
    url = f"https://api.sofascore.com/api/v1/event/{event_id}/statistics"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return

        data = res.json()
        statistics = data.get("statistics", [])

        for period in statistics:
            if period.get("period") == "ALL":
                groups = period.get("groups", [])
                for group in groups:
                    for item in group.get("statisticsItems", []):
                        if item.get("name") in ["Big chances", "Grandes chances"]:
                            val_home = int(item.get("home", 0))
                            val_away = int(item.get("away", 0))
                            total_chances_jogo = val_home + val_away
                            placar_atual_str = f"{current_home_score}-{current_away_score}"

                            # 1. Primeiro cadastro do jogo no monitor
                            if event_id not in historico_jogos:
                                # Se o placar for 0-0, carrega as chances acumuladas desde o início da partida
                                # Se já começou em outro placar, inicia do zero para aquele placar
                                chances_iniciais = total_chances_jogo if placar_atual_str == "0-0" else 0

                                historico_jogos[event_id] = {
                                    "score": placar_atual_str,
                                    "chances_no_placar": chances_iniciais,
                                    "last_total_chances": total_chances_jogo,
                                    "notificado": False
                                }
                                print(f"✅ Monitorando: {home_team} ({current_home_score}) x ({current_away_score}) {away_team} | Chances no placar: {chances_iniciais}")

                                # Se o jogo já for capturado no 0-0 e JÁ tiver 3 ou mais chances acumuladas, envia alerta imediatamente
                                if placar_atual_str == "0-0" and chances_iniciais >= 3:
                                    msg = (
                                        f"🎯 **ALERTA: 3+ CHANCES SEM GOL!**\n\n"
                                        f"⚽ Placar Mantido: **{home_team} {current_home_score} x {current_away_score} {away_team}**\n"
                                        f"🔥 Grandes chances acumuladas no 0x0: **{chances_iniciais}**\n"
                                        f"📊 Distribuição: {val_home} (Mandante) x {val_away} (Visitante)"
                                    )
                                    enviar_telegram(msg)
                                    historico_jogos[event_id]["notificado"] = True
                                return

                            dados = historico_jogos[event_id]

                            # 2. Se o placar MUDOU (saiu gol), reseta a contagem para o novo placar
                            if placar_atual_str != dados["score"]:
                                dados["score"] = placar_atual_str
                                dados["chances_no_placar"] = 0
                                dados["last_total_chances"] = total_chances_jogo
                                dados["notificado"] = False
                                print(f"⚽ GOL! {home_team} x {away_team} -> Placar: {placar_atual_str}. Contagem resetada.")
                                return

                            # 3. Se houver nova grande chance no mesmo placar
                            if total_chances_jogo > dados["last_total_chances"]:
                                novas_chances = total_chances_jogo - dados["last_total_chances"]
                                dados["chances_no_placar"] += novas_chances
                                dados["last_total_chances"] = total_chances_jogo

                                # Dispara o alerta se atingiu 3+ chances no mesmo placar e ainda não notificou para esse acúmulo
                                if dados["chances_no_placar"] >= 3 and not dados["notificado"]:
                                    msg = (
                                        f"🎯 **ALERTA: 3+ CHANCES SEM GOL!**\n\n"
                                        f"⚽ Placar Mantido: **{home_team} {current_home_score} x {current_away_score} {away_team}**\n"
                                        f"🔥 Grandes chances criadas neste mesmo placar: **{dados['chances_no_placar']}**\n"
                                        f"📊 Total no Jogo: {val_home} (Mandante) x {val_away} (Visitante)"
                                    )
                                    enviar_telegram(msg)
                                    dados["notificado"] = True

    except Exception:
        pass

def executar():
    print("🤖 Robô Atualizado (Contagem Mantida para 0x0) Iniciado!")
    while True:
        eventos = obter_jogos_sofascore()
        print(f"\n⚽ {len(eventos)} jogos ao vivo em análise...")

        for ev in eventos:
            event_id = ev.get("id")
            home_team = ev.get("homeTeam", {}).get("name")
            away_team = ev.get("awayTeam", {}).get("name")

            home_score = ev.get("homeScore", {}).get("current", 0)
            away_score = ev.get("awayScore", {}).get("current", 0)

            if event_id and home_team and away_team:
                checar_big_chances_e_placar(event_id, home_team, away_team, home_score, away_score)
                time.sleep(0.2)

        time.sleep(30)

if __name__ == "__main__":
    executar()
