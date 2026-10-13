"""Print the actual configured vault locally, without calling any provider."""
from dotenv import load_dotenv
from cronos.config import Settings

def main():
    load_dotenv('.env',override=True)
    vault=Settings.from_env().vault
    print('Pasta principal do Obsidian:',vault)
    print('Temas:',vault/'Temas')
    print('Informações significativas:',vault/'Memorias')
    print('Histórico de conversa (fora da espiral):',vault/'Conversas')
    print('Banco de dados local:',vault/'.cronos'/'memory.sqlite3')
    from cronos.conversation_metrics import read
    timings=read()
    if timings:
        print('Última conversa: tempos do backend em milissegundos (não inclui microfone nem síntese Fish):')
        for key,label in [('recall','Busca de memória'),('generation','Geração da IA'),('memory_write','Gravação da memória'),('total','Total')]:
            print(label+':',timings.get(key,'indisponível'))

if __name__=='__main__':main()
