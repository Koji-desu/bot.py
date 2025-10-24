import asyncio
from datetime import datetime
from fastapi import logger
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
import extrator
import os
from extensoes import db
from models import Usuario, Aposta
import requests


# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("📩 Recebi /start do usuário")
    await update.message.reply_text("Bot ativo! Envie uma imagem da aposta para extrair os dados.")

# Processa imagem enviada
async def processar_imagem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    foto = update.message.photo[-1]
    caminho = f"imagem_{update.message.message_id}.png"
    arquivo = await foto.get_file()
    await arquivo.download_to_drive(caminho)

    texto = extrator.extrair_texto_imagem(caminho)
    odd = extrator.extrair_odd_aposta(texto)
    aposta = extrator.extrair_valor_aposta(texto)
    retorno = extrator.extrair_valor_retorno(texto)
    data_aposta = extrator.extrair_data(texto)

    print(texto)
    print("-----------------------------------")
    print(f"Aposta: {aposta}, Retorno: {retorno}, Odd: {odd}", "Data:", {data_aposta})
    os.remove(caminho)

    if aposta == retorno:
        resultado = 'Cash Out'
    elif str(retorno) == '0,00':
        resultado = 'Perda'
    else:
        resultado = 'Ganho'

    if aposta and retorno and odd:
        dados = [data_aposta, aposta, odd, resultado, retorno]
        context.user_data["dados_pendentes"] = dados
        context.user_data["texto_ocr"] = texto
        await update.message.reply_text(
            f"Aposta: {aposta}\nRetorno: {retorno}\nOdd: {odd}\nDeseja enviar para a planilha?\nUse /confirmar ou /cancelar"
        )
    else:
        await update.message.reply_text("Não consegui extrair os dados da imagem.")

# Confirma envio
async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dados = context.user_data.get("dados_pendentes")
    usuario_id = context.user_data.get("usuario_id")
    if not usuario_id:
        await update.message.reply_text("⚠️ Você precisa verificar seu telefone antes de usar este comando. Use /telefone.")
        return

    if dados:
        payload = {
            "data": datetime.strptime(dados[0], "%d/%m/%Y").date().isoformat(),
            "valor_aposta": dados[1],
            "odd": dados[2],
            "resultado": dados[3],
            "retorno": dados[4],
            "usuario_id": usuario_id
        }

        response = requests.post("https://planilhatudo.onrender.com/api/aposta", json=payload)
        if response.status_code == 201:
            await update.message.reply_text("✅ Dados enviados com sucesso!")
            context.user_data.pop("dados_pendentes", None)
        else:
                logger.error("❌ Erro ao enviar os dados:")
                logger.error("Status code: %s", response.status_code)
                logger.error("Resposta: %s", response.text)

                await update.message.reply_text("❌ Erro ao enviar os dados.")
    else:
        await update.message.reply_text("Não há dados pendentes para enviar.")

# Cancela envio
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Envio cancelado. Os dados foram descartados.")

# Solicita telefone
async def solicitar_telefone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    teclado = [[KeyboardButton("📱 Enviar telefone", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(teclado, one_time_keyboard=True)
    await update.message.reply_text("Por favor, envie seu número de telefone:", reply_markup=reply_markup)

# Recebe telefone
async def receber_telefone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contato = update.message.contact
    telefone = contato.phone_number
    print(f"📲 Telefone recebido do Telegram: {telefone}")

    response = requests.get(f"https://planilhatudo.onrender.com/api/usuario?tel={telefone}")
    if response.status_code == 200:
        usuario = response.json()
        context.user_data["usuario_id"] = usuario["id"]
        await boas_vindas(update, context, usuario)
    else:
        await update.message.reply_text("❌ Telefone não encontrado. Faça cadastro no site.")

# Mensagem de boas-vindas
async def boas_vindas(update: Update, context: ContextTypes.DEFAULT_TYPE, usuario):
    mensagem = (
        f"👋 Olá, {usuario['nome']}!\n\n"
        "Seja bem-vindo de volta ao nosso sistema de apostas. 🎯\n"
        "Você já pode enviar uma imagem da sua aposta para que eu extraia os dados automaticamente.\n\n"
        "📌 Lembre-se: após o processamento, use /confirmar para salvar na planilha e no sistema.\n"
        "Se quiser cancelar, é só usar /cancelar.\n\n"
        "Vamos nessa? 💪"
    )
    await update.message.reply_text(mensagem)

# Inicializa bot
async def main():
    print("🔄 Iniciando bot Telegram...")
    token = "8491501717:AAGA_K3A4kqpvpWwvkjiMDntMGJpb0ui_E8" # Recomendo usar variável de ambiente
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("confirmar", confirmar))
    app.add_handler(CommandHandler("cancelar", cancelar))
    app.add_handler(CommandHandler("telefone", solicitar_telefone))
    app.add_handler(MessageHandler(filters.CONTACT, receber_telefone))
    app.add_handler(MessageHandler(filters.PHOTO, processar_imagem))

    await app.run_polling()

# Executa com loop compatível
import nest_asyncio
nest_asyncio.apply()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
