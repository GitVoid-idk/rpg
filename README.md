# Diário da Campanha

Site em tempo real para RPG: o mestre narra, os jogadores escrevem suas ações,
e um botão de D20 rola o dado (o resultado é só o número — quem decide se deu
certo é o mestre).

## Rodando localmente

```bash
pip install -r requirements.txt
python main.py
```

Depois acesse `http://localhost:8000`.

## Hospedando no Render (grátis)

1. Crie um repositório no GitHub e suba esta pasta inteira nele.
2. Entre em [render.com](https://render.com) e crie uma conta (não precisa cartão).
3. Clique em **New +** → **Web Service** e conecte o repositório do GitHub.
4. O Render deve detectar o `render.yaml` automaticamente e preencher tudo.
   Se pedir manualmente:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free
5. Clique em **Deploy**. Em alguns minutos você recebe uma URL tipo
   `https://campanha-rpg.onrender.com` — é esse link que você compartilha
   com seu primo.

### Sobre persistência dos dados (importante)

No plano gratuito do Render, o serviço "dorme" depois de 15 minutos sem uso,
e quando ele reinicia, qualquer arquivo local (como o `campanha.db` do
SQLite) é apagado. Ou seja, sem um banco externo, o histórico da campanha
pode se perder de tempos em tempos.

Para evitar isso, crie também um banco Postgres gratuito no Render:

1. **New +** → **PostgreSQL** → escolha o plano Free.
2. Copie a **Internal Database URL** gerada.
3. No seu Web Service, vá em **Environment** e adicione a variável:
   - `DATABASE_URL` = (a URL que você copiou)
4. Redeploy o serviço.

O banco Postgres gratuito expira 30 dias após a criação (o Render avisa por
e-mail antes), então de tempos em tempos você precisa recriá-lo — mas para
uma campanha entre você e seu primo isso costuma ser suficiente.

Se preferir simplicidade e não se importar em perder o histórico
ocasionalmente, pode simplesmente não configurar `DATABASE_URL` e deixar
no SQLite local.
