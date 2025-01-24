import os
import random
import re
from datetime import datetime
import shutil
from apscheduler.schedulers.blocking import BlockingScheduler
from atproto import Client, models


# ==============================================================================
# VARIÁBEIS
# ==============================================================================
# Configuración desde variables de entorno o archivo de configuración
BLUESKY_USERNAME = os.getenv("BLUESKY_USERNAME")
BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD")

DIRECTORY_SOURCE = os.getenv("DIRECTORY_SOURCE")
DIRECTORY_DESTINATION = os.getenv("DIRECTORY_DESTINATION")

LETRAS_BASICAS = "A-Za-z"
LETRAS_ESPECIAIS = "çñáàãéèêíìîóòõúùûÇÑÁÀÃÉÈÊÍÌÎÓÒÕÚÙÛ1234567890"
LETRAS_SIMBOLOS = r"\.\+\-\_\(\)\[\]\{\}\!\?\¿\¡\,\'\:\;\&\%\$\#\@\*\/"
LETRAS_GLPT = f"{LETRAS_BASICAS}{LETRAS_ESPECIAIS}{LETRAS_SIMBOLOS}"


# ==============================================================================
# CLASE
# ==============================================================================
class BlueskyDailyBot:

    dir_source = "/source_dir"
    dir_destination = "/destination_dir"

    def __init__(self, bluesky_username, bluesky_password):
        """
        Inicializa el bot de Bluesky.

        :param arte_dir: Directorio donde se encuentran las imágenes
        :param bluesky_username: Nombre de usuario de Bluesky
        :param bluesky_password: Contraseña de Bluesky
        """
        self.client = Client()
        try:
            print(bluesky_username, bluesky_password)
            self.client.login(bluesky_username, bluesky_password)
            print("Autenticação certa.")

            
        except Exception as e:
            print(f"Erro de autenticação: {e}")
            self.client.me = (
                None  # Asegúrate de que me sea None si hay un error
            )
    
    def validar_arquivo(self, arquivo):
        pattern1 = rf"^[{LETRAS_GLPT} ]+, [{LETRAS_GLPT} ]+ \(\d{{4}}\) - [{LETRAS_GLPT} ]+ \([{LETRAS_GLPT} ]+\)\.(jpg|jpeg|png|gif)$"
        pattern2 = rf"^[{LETRAS_GLPT} ]+ \(((ca\. )*(c\. )*(\d{{4}}\))|(\d{{4}}-\d{{2}})) - [{LETRAS_GLPT} ]+ \([{LETRAS_GLPT} ]+\)\.(jpg|jpeg|png|gif)$"
        
        match1 = re.match(pattern1, arquivo)
        match2 = re.match(pattern2, arquivo)
        
        if match1 or match2:
            #print(f"Arquivo válido: {arquivo}")
            return True
        else:
            #print(f"Arquivo não válido: {arquivo}")
            return False


    def selecionar_arquivo(self):
        """
        Seleciona um arquivo aleatório do diretório de origem.
        """
        try:
            # Lista os arquivos do diretório
            arquivos = os.listdir(self.dir_source)
            print(f"Archivos encontrados en {self.dir_source}: {len(arquivos)}")

            if not arquivos:
                print("\tNão se encontraron arquivos na origem.")
                return None


            arquivo_certo = False
            i = 0

            while not arquivo_certo:
                # Seleciona um arquivo aleatório
                arquivo = random.choice(arquivos)
                print(f"\tProbamos con '{arquivo}'")
                i += 1

                if i > 10:
                    print("\tDemasiados intentos para selecionar o arquivo.")
                    return None

                if self.validar_arquivo(arquivo):
                    arquivo_certo = True
                    print(f"\tArquivo selecionado: {arquivo}")
            
            return arquivo

        except FileNotFoundError:
            print(f"El directorio {self.dir_source} no existe.")
            return None
        except PermissionError:
            print(f"No se tienen permisos para acceder al directorio {self.dir_source}.")
            return None
        except Exception as e:
            print(f"Erro ao selecionar arquivo: {e}")
            return None

    def mover_archivo(self, archivo):
        """
        Mueve un archivo de origen a destino.
        """
        try:
            # Mueve el archivo al directorio de destino
            shutil.move(
                f"{self.dir_source}/{archivo}",
                f"{self.dir_destination}/{archivo}",
            )
            print(f"Archivo movido: {archivo}")

        except Exception as e:
            print(f"Error al mover archivo: {e}")

    def publicar_en_bluesky(self, archivo):
        """
        Publica una imagen en Bluesky con su descripción correspondiente.
        """
        try:
            # Leer el archivo de imagen
            with open(f"{self.dir_source}/{archivo}", "rb") as img_file:
                img_data = img_file.read()

            # Subir la imagen a Bluesky
            img_resp = self.client.com.atproto.repo.upload_blob(img_data)
            img_cid = img_resp["cid"]

            # Crear post con la imagen
            post = models.AppBskyFeedPost.Record(
                text=archivo,
                embed=models.AppBskyFeedPost.RecordEmbed(
                    images=[
                        models.AppBskyFeedPost.RecordEmbedImage(
                            image=img_cid, alt=archivo
                        )
                    ]
                ),
                created_at=datetime.now().isoformat() + "Z",
            )

            self.client.com.atproto.repo.create_record(
                models.ComAtprotoRepoCreateRecord.Data(
                    repo=self.client.me.did,
                    collection="app.bsky.feed.post",
                    record=post,
                )
            )
            print(f"Publicación exitosa: {archivo}")

        except Exception as e:
            print(f"Error al publicar: {e}")


# ==============================================================================
# MAIN
# ==============================================================================
def publicar():

    bot = BlueskyDailyBot(
        bluesky_username=BLUESKY_USERNAME, bluesky_password=BLUESKY_PASSWORD
    )

    print("⌛ Bot configurado. Programando publicaciones...")

    try:
        arquivo = bot.selecionar_arquivo()
        print(f"Seleccionando archivo en {bot.dir_source}")

        try:
            bot.publicar_en_bluesky(arquivo)
        except Exception as e:
            print(f"Error al publicar: {e}")

            try:
                print(f"Moviendo archivo {arquivo} a {bot.dir_destination}")
                bot.mover_archivo(arquivo)
            except Exception as e:
                print(f"Error al mover archivo: {e}")

    except Exception as e:
        print(f"Error al seleccionar archivo: {e}")

    
    
    

def main():

    # Programar publicación diaria a las 20:00
    scheduler = BlockingScheduler(timezone="Europe/Madrid")
    #scheduler.add_job(publicar, "cron", hour=21, minute=0)
    scheduler.add_job(publicar, "interval", seconds=10)

    try:
        print("🦋 Bot iniciado. Esperando hora de publicación...")
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Parando o bot...")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
