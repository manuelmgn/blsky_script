import os
import random
import re
from datetime import datetime
import shutil
from apscheduler.schedulers.blocking import BlockingScheduler
from atproto import Client, models
from dotenv import load_dotenv
from PIL import Image


load_dotenv()

# ==============================================================================
# VARIÁVEIS
# ==============================================================================

BLUESKY_USERNAME = os.getenv("BLUESKY_USERNAME")
BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD")

DIRECTORY_SOURCE = os.getenv("DIRECTORY_SOURCE")
DIRECTORY_DESTINATION = os.getenv("DIRECTORY_DESTINATION")


# ==============================================================================
# CLASSE
# ==============================================================================
class BlueskyDailyBot:

    def __init__(self, bluesky_username, bluesky_password):
        """
        Inicializa o bot de Bluesky.

        Args:
            bluesky_username (str): Nome de usuário de Bluesky.
            bluesky_password (str): Senha de Bluesky.
        """
        self.client = Client()
        self.dir_source = DIRECTORY_SOURCE
        self.dir_destination = DIRECTORY_DESTINATION

        try:
            self.client.login(bluesky_username, bluesky_password)
            print("🔐 Autenticação certa.")

        except Exception as e:
            print(f"Erro de autenticação: {e}")
            self.client.me = None

    def selecionar_arquivo(self):
        """
        Seleciona um arquivo aleatório do diretório de origem.

        Returns:
            str: Nome do arquivo selecionado.
        """
        try:
            # Lista os arquivos do diretório
            arquivos = os.listdir(self.dir_source)
            if not arquivos:
                raise FileNotFoundError("❌ O diretório está vazio.")

            print(f"🔎 {len(arquivos)} arquivos en {self.dir_source}")

            arquivo_certo = False
            i = 0

            arquivo = ""

            while not arquivo_certo:
                # Seleciona um arquivo aleatório
                arquivo = random.choice(arquivos)
                print(f"\tProbamos con '{arquivo}'")
                i += 1

                if i > 20:
                    print("\tDemasiadas tentativas para escolher o arquivo.")
                    return None

                if self.validar_arquivo(arquivo):
                    arquivo_certo = True
                    print(f"\tArquivo selecionado: {arquivo}")

            if not arquivo:
                print("\tNão se encontrou un arquivo válido.")
                return None

            try:
                self.comprimir_arquivo(arquivo)
            except Exception as e:
                print(f"Erro ao comprimir o arquivo: {e}")

            return arquivo

        except PermissionError:
            print(
                f"Não se têm permisso para aceder ao diretório {self.dir_source}."
            )
            return None
        except Exception as e:
            print(f"Erro ao selecionar arquivo: {e}")
            return None

    def validar_arquivo(self, arquivo):
        """
        Valida se o arquivo tem o formato correto.

        Args:
            arquivo (str): Nome do arquivo.

        Returns:
            bool: True se o arquivo for válido, False caso contrário.
        """

        pattern1 = rf"^(((.*?), (.*?))|(.*?)) (\(\d{{4}}\) )?- (.*?) \((.*?)\)\.(jpg|jpeg|png|gif)$"
        pattern2 = rf"^(((.*?), (.*?))|(.*?)) (\(((ca\. )*(c\. )*(\d{{4}}\))|(\d{{4}}-\d{{2}})) ?)- (.*?) \((.*?)\)\.(jpg|jpeg|png|gif)$"

        match1 = re.match(pattern1, arquivo)
        match2 = re.match(pattern2, arquivo)

        if match1 or match2:
            # print(f"Arquivo válido: {arquivo}")
            return True
        else:
            # print(f"Arquivo não válido: {arquivo}")
            return False

    def comprimir_arquivo(self, arquivo):
        """
        Comprime um arquivo de imagem se o tamanho for maior que 976.56 KB.
        """
        arquivo_path = os.path.join(self.dir_source, arquivo)
        tamanho_max = 976.56 * 1024

        if os.path.getsize(arquivo_path) >= tamanho_max:
            print(f"📦 Comprimindo {arquivo}...")

            try:
                with Image.open(arquivo_path) as img:
                    img = img.convert("RGB")
                    arquivo_comprimido_path = os.path.join(
                        self.dir_source, f"comprimido_{arquivo}"
                    )
                    img.save(arquivo_comprimido_path, "JPEG", quality=85)
                    print(
                        f"Arquivo comprimido gardado como {arquivo_comprimido_path}"
                    )

            except Exception as e:
                print(f"Erro ao comprimir o arquivo {arquivo}: {e}")

        else:
            shutil.copy(
                arquivo_path,
                os.path.join(self.dir_source, f"comprimido_{arquivo}"),
            )

    def publicar_en_bluesky(self, arquivo):
        """
        Publica uma imagem em Bluesky.

        Args:
            arquivo (str): Nome do arquivo.

        Returns:
            bool: True se a publicação for bem-sucedida, False caso contrário.
        """
        try:
            with open(
                f"{self.dir_source}/comprimido_{arquivo}", "rb"
            ) as img_file:
                img_data = img_file.read()

            nome = img_file.name
            nome = self.sanitize_filename(nome)

            self.client.send_image(
                text=nome,
                image=img_data,
                image_alt=nome,
            )

            print("👍 Publicado en Bluesky.")

        except Exception as e:
            print(f"Erro ao publicar: {e}")

    def sanitize_filename(self, nome):
        replacements = [
            "/source_dir/comprimido_",
            "comprimido_",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
        ]

        for r in replacements:
            nome = nome.replace(r, "")
        return nome

    def mover_arquivo(self, arquivo):
        """
        Move um arquivo para o diretório de destino.

        Args:
            arquivo (str): Nome do arquivo.

        Returns:
            bool: True se o arquivo for movido com sucesso, False caso contrário
        """
        try:
            # Mueve el arquivo al directorio de destino
            os.remove(f"{self.dir_source}/comprimido_{arquivo}")

            shutil.move(
                f"{self.dir_source}/{arquivo}",
                f"{self.dir_destination}/{arquivo}",
            )

            print(f"🚛 Arquivo movido: {arquivo}")

        except Exception as e:
            print(f"Erro ao mover o arquivo: {e}")


# ==============================================================================
# MAIN
# ==============================================================================
def publicar():

    bot = BlueskyDailyBot(
        bluesky_username=BLUESKY_USERNAME, bluesky_password=BLUESKY_PASSWORD
    )

    print("⌛ Bot configurado. Programando publicações...")

    try:
        arquivo = bot.selecionar_arquivo()
        bot.publicar_en_bluesky(arquivo)
        bot.mover_arquivo(arquivo)

    except Exception as e:
        print(f"Erro ao publicar: {e}")


def main():
    
    print("----------------------------\n")

    scheduler = BlockingScheduler(timezone="Europe/Madrid")
    # scheduler.add_job(publicar, "cron", hour=21, minute=0)
    scheduler.add_job(publicar, "interval", seconds=10)

    try:
        print("🦋 Bot iniciado. Esperando a hora para publicar...")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Parando o bot...")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
