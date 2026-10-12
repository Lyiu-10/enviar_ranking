"""Ranking de gastos por evento. Roda com: python server.py
TV abre  http://<ip-do-notebook>:8000/        (ranking)
Notebook http://localhost:8000/admin          (lançamentos)
Dados ficam em dados.json, nesta pasta, com uma cópia por dia em backups/."""
import json, os, socket, sys, time, unicodedata, webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

PASTA = os.path.dirname(os.path.abspath(__file__))
ARQ = os.path.join(PASTA, "dados.json")
BACKUPS = os.path.join(PASTA, "backups")
PORTA = 8000
CATEGORIAS = ["Salgados", "Sucos", "Doces"]  # nesta ordem no caixa
CARDAPIO_INICIAL = [  # ajuste no caixa, em ⚙ Configurações
    {"nome": "🍝 Lasanha de carne", "preco": 5, "cat": "Salgados"},
    {"nome": "🍝 Lasanha de frango", "preco": 5, "cat": "Salgados"},
    {"nome": "🥩 Carne de sol na nata", "preco": 6, "cat": "Salgados"},
    {"nome": "🥧 Empadão", "preco": 6, "cat": "Salgados"},
    {"nome": "🥣 Creme de frango", "preco": 5, "cat": "Salgados"},
    {"nome": "🍟 Batata frita", "preco": 5, "cat": "Salgados"},
    {"nome": "🍗 Frango em tiras empanado", "preco": 5, "cat": "Salgados"},
    {"nome": "🧆 Nuggets", "preco": 5, "cat": "Salgados"},
    {"nome": "🌭 Monte seu cachorro-quente", "preco": 6, "cat": "Salgados"},
    {"nome": "🦐 Creme de camarão", "preco": 6, "cat": "Salgados"},
    {"nome": "🍤 Camarão empanado", "preco": 6, "cat": "Salgados"},
    {"nome": "🦞 Caldo de lagosta", "preco": 6, "cat": "Salgados"},
    {"nome": "🍓 Suco de morango com maracujá", "preco": 4, "cat": "Sucos"},
    {"nome": "🍍 Suco de abacaxi com hortelã", "preco": 4, "cat": "Sucos"},
    {"nome": "🍊 Suco de laranja feito na hora", "preco": 4, "cat": "Sucos"},
    {"nome": "🥭 Suco de manga", "preco": 4, "cat": "Sucos"},
    {"nome": "🥥 Água de coco", "preco": 5, "cat": "Sucos"},
    {"nome": "🍪 Alfajor", "preco": 4, "cat": "Doces"},
    {"nome": "🍰 Torta holandesa", "preco": 5, "cat": "Doces"},
    {"nome": "🍮 Pudim", "preco": 5, "cat": "Doces"},
    {"nome": "🍧 Dindin gourmet", "preco": 4, "cat": "Doces"}]


def carregar():
    if not os.path.exists(ARQ):
        return {"evento": "Dia das Crianças", "lancamentos": [], "cardapio": CARDAPIO_INICIAL}
    with open(ARQ, encoding="utf-8") as f:
        d = json.load(f)
    d.setdefault("cardapio", CARDAPIO_INICIAL)
    padrao = {i["nome"]: i["cat"] for i in CARDAPIO_INICIAL}
    for i in d["cardapio"]:  # cardápio salvo antes das categorias
        i.setdefault("cat", padrao.get(i["nome"], CATEGORIAS[0]))
    return d


def salvar(d):
    texto = json.dumps(d, ensure_ascii=False, indent=1)
    tmp = ARQ + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(texto)
    os.replace(tmp, ARQ)  # troca atômica: nunca deixa o arquivo pela metade
    os.makedirs(BACKUPS, exist_ok=True)
    with open(os.path.join(BACKUPS, f"dados-{datetime.now():%Y-%m-%d}.json"), "w", encoding="utf-8") as f:
        f.write(texto)


def chave(nome):
    """'  maria  FERNÁNDES' e 'Maria Fernandes' são a mesma pessoa."""
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


def valor_br(v):
    """'R$ 1.250,90' -> 1250.9 · '10,5' -> 10.5 · '10.50' -> 10.5"""
    s = str(v).replace("R$", "").replace(" ", "")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return round(float(s), 2)


def ranking(d):
    tot, nomes, avatar = {}, {}, {}
    for l in d["lancamentos"]:
        k = chave(l["nome"])
        avatar.setdefault(k, len(avatar))  # ordem de chegada no sistema todo: bonequinho fixo e sem repetir
        if l["evento"] != d["evento"]:
            continue
        tot[k] = tot.get(k, 0) + l["valor"]
        nomes.setdefault(k, l["nome"])
    ordem = sorted(tot, key=lambda k: -tot[k])  # empate: quem chegou primeiro fica na frente
    return [{"id": k, "nome": nomes[k], "total": round(tot[k], 2), "av": avatar[k]} for k in ordem]


def vendas(d):
    """Quanto saiu de cada item no evento atual, lido do texto '2× 🍝 Lasanha, 1× 🍮 Pudim' de cada lançamento."""
    precos = {i["nome"]: i["preco"] for i in d["cardapio"]}
    qtd, total, pedidos = {}, 0, 0
    for l in d["lancamentos"]:
        if l["evento"] != d["evento"]:
            continue
        total += l["valor"]
        pedidos += 1
        for parte in l.get("itens", "").split(", "):
            n, _, nome = parte.partition("× ")
            if n.isdigit() and nome in precos:
                qtd[nome] = qtd.get(nome, 0) + int(n)
    # ponytail: valor do item = preço atual do cardápio; se mudar o preço no meio do evento, a conta por item muda junto
    itens = [{"nome": n, "qtd": q, "valor": round(q * precos[n], 2)} for n, q in sorted(qtd.items(), key=lambda x: -x[1])]
    return {"total": round(total, 2), "pedidos": pedidos, "itens": itens,
            "outros": round(total - sum(i["valor"] for i in itens), 2)}


class H(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _arquivo(self, nome):
        with open(os.path.join(PASTA, nome), "rb") as f:
            b = f.read()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        d = carregar()
        if self.path == "/":
            return self._arquivo("ranking.html")
        if self.path == "/admin":
            return self._arquivo("admin.html")
        if self.path == "/api/ranking":  # para a TV: sem valores
            top = [{"id": p["id"], "nome": p["nome"], "av": p["av"]} for p in ranking(d)[:10]]
            return self._json({"evento": d["evento"], "top": top})
        if self.path == "/api/estado":  # para o admin: com valores
            unicos = {}
            for l in d["lancamentos"]:
                unicos.setdefault(chave(l["nome"]), l["nome"])
            ultimos = [l for l in d["lancamentos"] if l["evento"] == d["evento"]][-30:][::-1]
            eventos = list(dict.fromkeys(l["evento"] for l in d["lancamentos"]))
            return self._json({"evento": d["evento"], "ranking": ranking(d), "ultimos": ultimos,
                               "pessoas": [{"id": k, "nome": n} for k, n in sorted(unicos.items())],
                               "eventos": eventos, "cardapio": d["cardapio"], "categorias": CATEGORIAS, "vendas": vendas(d)})
        self.send_error(404)

    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except ValueError:
            return self._json({"erro": "JSON inválido"}, 400)
        d = carregar()
        if self.path == "/api/lancar":
            nome = " ".join(str(body.get("nome", "")).split())
            try:
                valor = valor_br(body.get("valor"))
            except ValueError:
                valor = 0
            if not nome or valor <= 0:
                return self._json({"erro": "Preencha nome e um valor maior que zero"}, 400)
            d["lancamentos"].append({"id": str(time.time_ns()), "evento": d["evento"], "nome": nome,
                                     "valor": valor, "itens": str(body.get("itens", ""))[:300],
                                     "quando": datetime.now().isoformat(timespec="seconds")})
        elif self.path == "/api/apagar":
            d["lancamentos"] = [l for l in d["lancamentos"] if l.get("id") != body.get("id")]
        elif self.path == "/api/cardapio":
            try:
                itens = [{"nome": " ".join(str(i["nome"]).split()), "preco": valor_br(i["preco"]),
                      "cat": i.get("cat") if i.get("cat") in CATEGORIAS else CATEGORIAS[0]}
                         for i in body.get("cardapio", [])]
            except (KeyError, TypeError, ValueError):
                return self._json({"erro": "Confira os preços do cardápio"}, 400)
            if not itens or any(not i["nome"] or i["preco"] <= 0 for i in itens):
                return self._json({"erro": "Todo item precisa de nome e preço maior que zero"}, 400)
            d["cardapio"] = itens
        elif self.path == "/api/evento":
            ev = " ".join(str(body.get("evento", "")).split())
            if not ev:
                return self._json({"erro": "Dê um nome ao evento"}, 400)
            iguais = [l["evento"] for l in d["lancamentos"] if chave(l["evento"]) == chave(ev)]
            d["evento"] = iguais[0] if iguais else ev  # histórico fica guardado; o ranking só conta o evento atual
        else:
            return self.send_error(404)
        salvar(d)
        self._json({"ok": True})

    def log_message(self, *a):
        pass


def ip_local():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "localhost"


def teste():
    d = {"evento": "A", "lancamentos": [
        {"evento": "B", "nome": "Zé", "valor": 999},
        {"evento": "A", "nome": "Maria", "valor": 10},
        {"evento": "A", "nome": "Fernando", "valor": 5},
        {"evento": "A", "nome": "fernando ", "valor": 7},
        {"evento": "A", "nome": "MARÍA", "valor": 1}]}
    r = ranking(d)
    assert [(p["nome"], p["total"], p["av"]) for p in r] == [("Fernando", 12, 2), ("Maria", 11, 1)], r
    d["evento"] = "B"
    assert [p["nome"] for p in ranking(d)] == ["Zé"]
    d = {"evento": "A", "cardapio": [{"nome": "🍮 Pudim", "preco": 5}, {"nome": "🍪 Alfajor", "preco": 4}], "lancamentos": [
        {"evento": "A", "valor": 14, "itens": "2× 🍮 Pudim, 1× 🍪 Alfajor"},
        {"evento": "A", "valor": 17.5, "itens": "1× 🍮 Pudim, 1× Outro valor R$ 12,50"},
        {"evento": "B", "valor": 99, "itens": "9× 🍮 Pudim"}]}
    assert vendas(d) == {"total": 31.5, "pedidos": 2, "outros": 12.5, "itens": [
        {"nome": "🍮 Pudim", "qtd": 3, "valor": 15}, {"nome": "🍪 Alfajor", "qtd": 1, "valor": 4}]}, vendas(d)
    assert valor_br("R$ 1.250,90") == 1250.9 and valor_br("10,5") == 10.5 and valor_br("10.50") == 10.5
    print("ok")


if __name__ == "__main__":
    if "--teste" in sys.argv:
        teste()
        sys.exit()
    ip = ip_local()
    print(f"\n  RANKING (TV):  http://{ip}:{PORTA}/")
    print(f"  ADMIN:         http://localhost:{PORTA}/admin")
    print(f"  Dados em:      {ARQ}\n  Feche esta janela para desligar.\n")
    # uma thread só: dois lançamentos nunca se atropelam no arquivo
    srv = HTTPServer(("0.0.0.0", PORTA), H)
    webbrowser.open(f"http://localhost:{PORTA}/admin")
    srv.serve_forever()
