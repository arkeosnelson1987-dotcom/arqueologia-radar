# Arqueologia Radar — Web/PWA

Esta é a arquitetura destinada a funcionar **apenas no iPad**, através do Safari, sem EXE, BAT, PowerShell ou instalação local.

## O que falta para ficar acessível na Internet

É necessário publicar esta pasta num serviço que execute Docker/FastAPI. Depois de publicado, o utilizador recebe um endereço HTTPS e pode no iPad escolher **Partilhar → Adicionar ao ecrã principal**.

## Pesquisa

O botão **PESQUISAR AGORA** é manual. Não existe scheduler nem envio de email.

A integração API efetiva incluída é TED. As restantes fontes estão catalogadas como portais oficiais e podem ser abertas diretamente. Isto evita alegar que uma fonte tem API quando não tem uma API pública adequada.

## Executar num servidor

`docker build -t arqueologia-radar .`

`docker run -p 8000:8000 arqueologia-radar`

Depois abrir `http://IP-DO-SERVIDOR:8000`.
