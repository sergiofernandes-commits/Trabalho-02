import serial
import struct
import time
import os
import math
import matplotlib.pyplot as plt
import numpy as np

# --- CONFIGURACOES ---
SERIAL_PORT = 'COM6'
BAUD_RATE = 115200

CMD_RECEIVE_INT = 1  
CMD_SEND_INT = 2     

# Guarda os últimos dados enviados e recebidos
ultimo_vetor_enviado = []
ultimo_vetor_recebido = []

FS_ADC = 5000.0

def gerar_vetor_dac_com_harmonicas(
        frequencia_onda,
        amostras_por_ciclo,
        dac_bits,
        amplitude_normalizada):

    max_dac_val = (2 ** dac_bits) - 1

    # Harmônicas fixas
    harmonicas = [
        (3, 0.15),   # 3ª harmônica = 15%
        (5, 0.05),   # 5ª harmônica = 5%
        (7, 0.03)    # 7ª harmônica = 3%
    ]

    vetor = []

    for i in range(amostras_por_ciclo):

        theta = 2 * math.pi * i / amostras_por_ciclo

        valor = math.sin(theta)

        for ordem, amp_rel in harmonicas:
            valor += amp_rel * math.sin(ordem * theta)

        vetor.append(valor)

    # Normalização
    max_abs = max(abs(v) for v in vetor)
    vetor = [v / max_abs for v in vetor]

    offset = max_dac_val / 2.0
    amplitude_dac = amplitude_normalizada * (max_dac_val / 2.0)

    dac_valores = []

    for v in vetor:

        valor_dac = offset + amplitude_dac * v

        valor_dac = int(round(
            max(0, min(valor_dac, max_dac_val))
        ))

        dac_valores.append(valor_dac)

    frequencia_amostragem = frequencia_onda * amostras_por_ciclo

    return dac_valores, frequencia_amostragem

def gerar_vetor_dac_parametrizado(frequencia_onda,
                                  amostras_por_ciclo,
                                  dac_bits,
                                  amplitude_normalizada):


    if amostras_por_ciclo <= 0:
        raise ValueError("O número de amostras deve ser > 0.")

    max_dac_val = (2 ** dac_bits) - 1

    offset = max_dac_val / 2.0
    amplitude_dac = amplitude_normalizada * (max_dac_val / 2.0)

    dac_valores = []

    for i in range(amostras_por_ciclo):
        valor = offset + amplitude_dac * math.sin(2 * math.pi * i / amostras_por_ciclo)
        dac_valores.append(int(round(max(0, min(valor, max_dac_val)))))

    frequencia_amostragem = frequencia_onda * amostras_por_ciclo

    return dac_valores, frequencia_amostragem


def salvar_vetor_em_arquivo_c(caminho,
                              vetor,
                              freq,
                              n_amostras,
                              res,
                              amp,
                              fs):
    """Salva o vetor em arquivo .c"""

    with open(caminho, 'w') as f:

        f.write("// Arquivo gerado automaticamente\n")
        f.write(f"#define FREQ_ONDA {freq}\n")
        f.write(f"#define NUM_AMOSTRAS {n_amostras}\n")
        f.write(f"#define RES_DAC {res}\n")
        f.write(f"#define AMP_NORM {amp}\n")
        f.write(f"#define FREQ_AMOSTRAGEM {fs}\n\n")

        f.write(f"const int16_t dac_buffer[{n_amostras}] = {{\n")

        f.write(",\n".join([f"    {val}" for val in vetor]))

        f.write("\n};\n")

    print(f"\nSucesso: Arquivo salvo em: {caminho}")


def receive_int(ser_connection):


    try:

        ser_connection.flushInput()

        request_packet = struct.pack('<Bh', CMD_SEND_INT, 0)

        ser_connection.write(request_packet)

        response_data = ser_connection.read(2)

        if not response_data or len(response_data) < 2:
            print("ERRO: Timeout.")
            return None

        received_number = struct.unpack('<h', response_data)[0]

        return received_number

    except Exception as e:
        print(f"Erro: {e}")
        return None


def plotar_comparacao(vetor_dac, vetor_adc):

    tamanho = min(len(vetor_dac), len(vetor_adc))

    vetor_dac = vetor_dac[:tamanho]
    vetor_adc = vetor_adc[:tamanho]

    erro = []

    for i in range(tamanho):
        erro.append(vetor_adc[i] - vetor_dac[i])

    print("\n===== ESTATISTICAS =====")
    print("Erro medio :", sum(erro) / len(erro))
    print("Erro maximo:", max(erro))
    print("Erro minimo:", min(erro))

    plt.figure(figsize=(12, 6))

    plt.plot(vetor_dac, label="DAC (Enviado)")
    plt.plot(vetor_adc, label="ADC (Recebido)")

    plt.grid(True)
    plt.xlabel("Amostra")
    plt.ylabel("Valor")
    plt.title("Comparacao DAC x ADC")
    plt.legend()

    plt.tight_layout()
    plt.show()

    plt.figure(figsize=(12, 4))

    plt.plot(erro)

    plt.grid(True)
    plt.xlabel("Amostra")
    plt.ylabel("Erro")
    plt.title("Erro = ADC - DAC")

    plt.tight_layout()
    plt.show()


import numpy as np
import matplotlib.pyplot as plt

import numpy as np
import matplotlib.pyplot as plt


def plotar_fft(sinal, fs, titulo, limite_f_hz=5000):

    sinal = np.array(sinal)

    # Usa apenas metade das amostras
    sinal = sinal[:len(sinal)//2]

    N = len(sinal)

    sinal_ac = sinal - np.mean(sinal)

    fft_vals = np.fft.rfft(sinal_ac)
    freqs = np.fft.rfftfreq(N, d=1 / fs)

    magnitude = np.abs(fft_vals) * 2 / N

    indice_pico = np.argmax(magnitude[1:]) + 1
    freq_dominante = freqs[indice_pico]
    mag_dominante = magnitude[indice_pico]

    print(f"\n--- Resultados: {titulo} ---")
    print(f"Número de amostras usadas: {N}")
    print(f"Frequência Dominante: {freq_dominante:.2f} Hz")
    print(f"Magnitude (Amplitude): {mag_dominante:.2f}")

    plt.figure(figsize=(10, 5))
    plt.plot(freqs, magnitude, linewidth=1.5)

    plt.annotate(
        f'Pico: {freq_dominante:.1f} Hz\nMag: {mag_dominante:.1f}',
        xy=(freq_dominante, mag_dominante),
        xytext=(freq_dominante + 20, mag_dominante),
        arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=5),
        fontsize=10,
        fontweight='bold'
    )

    plt.title(titulo)
    plt.xlabel("Frequência (Hz)")
    plt.ylabel("Magnitude")
    plt.grid(True)

    plt.xlim(0, limite_f_hz)
    plt.ylim(-10, mag_dominante * 1.3)

    plt.tight_layout()
    plt.show()




def comparar_fft(dac, adc, fs, limite_f_hz=500):
    dac = np.array(dac)
    adc = np.array(adc)
    N = min(len(dac), len(adc))
    dac, adc = dac[:N], adc[:N]

    # Normalização em relação a N
    fft_dac = np.fft.rfft(dac) * 2 / N
    fft_adc = np.fft.rfft(adc) * 2 / N
    freqs = np.fft.rfftfreq(N, d=1 / fs)

    plt.figure(figsize=(12, 6))
    plt.plot(freqs, np.abs(fft_dac), label="FFT DAC (Enviado)", alpha=0.8)
    plt.plot(freqs, np.abs(fft_adc), label="FFT ADC (Recebido)", alpha=0.8)

    plt.grid(True, which="both", ls="--", alpha=0.5)
    plt.xlabel("Frequência (Hz)")
    plt.ylabel("Magnitude")
    plt.title("Comparativo de Espectro: DAC vs ADC")

    # Zoom no eixo X
    plt.xlim(0, limite_f_hz)



    plt.legend()
    plt.tight_layout()
    plt.show()

def main():

    global ultimo_vetor_enviado
    global ultimo_vetor_recebido

    print("--- Terminal de Teste SCI para 28379D ---")

    try:

        with serial.Serial(SERIAL_PORT,
                           BAUD_RATE,
                           timeout=1) as ser:

            while True:

                print("1. Gerar, Salvar e ENVIAR forma de onda (PC -> MCU)")
                print("2. SOLICITAR e Receber 200 dados (MCU -> PC)")
                print("3. Comparar DAC x ADC")
                print("4. FFT do ADC")
                print("5. FFT DAC x ADC")
                print("6. Presenca e amplitude de harmonicas")
                print("0. Sair")

                choice = input("Escolha uma opcao: ")

                # ==================================================
                # OPCAO 1
                # ==================================================
                if choice == '1':

                    try:

                        f = float(input("Frequencia da onda (Hz): "))
                        n = int(input("Numero de amostras por ciclo: "))
                        bits = int(input("Resolucao do DAC (ex: 12): "))
                        amp = float(input("Amplitude normalizada (0 a 1): "))

                        vetor, fs = gerar_vetor_dac_parametrizado(
                            f,
                            n,
                            bits,
                            amp
                        )

                        ultimo_vetor_enviado = vetor.copy()

                        pasta_destino = r"C:\Users\Fernandes\Desktop\Trabalho Gulherme\DAC_ADC_EX\dac_adc_ex\utils"

                        if not os.path.exists(pasta_destino):
                            os.makedirs(pasta_destino)

                        caminho_completo = os.path.join(
                            pasta_destino,
                            "dac_buffer_values.c"
                        )

                        salvar_vetor_em_arquivo_c(
                            caminho_completo,
                            vetor,
                            f,
                            n,
                            bits,
                            amp,
                            fs
                        )

                        print(f"\nEnviando {len(vetor)} amostras...")

                        for val in vetor:

                            packet = struct.pack(
                                '<Bhh',
                                CMD_RECEIVE_INT,
                                2,
                                val
                            )

                            ser.write(packet)

                        print("Envio concluido.")

                    except Exception as e:
                        print(f"Erro: {e}")

                # ==================================================
                # OPCAO 2
                # ==================================================
                elif choice == '2':

                    dados = []

                    print("\nRecebendo 200 amostras...")

                    for i in range(200):

                        valor = receive_int(ser)

                        if valor is not None:
                            dados.append(valor)

                    if len(dados) == 0:
                        print("Nenhum dado recebido.")
                        continue

                    ultimo_vetor_recebido = dados.copy()

                    print("\nTotal recebido:", len(dados))
                    print("Min =", min(dados))
                    print("Max =", max(dados))
                    print("Primeiros 10 =", dados[:10])

                    plt.figure(figsize=(10, 5))

                    plt.plot(
                        range(len(dados)),
                        dados,
                        linewidth=2
                    )

                    plt.grid(True)
                    plt.xlabel("Amostra")
                    plt.ylabel("Valor ADC")
                    plt.title("Dados recebidos do F28379D")

                    plt.tight_layout()
                    plt.show()

                # ==================================================
                # OPCAO 3
                # ==================================================
                elif choice == '3':

                    if len(ultimo_vetor_enviado) == 0:
                        print("Nenhum vetor foi enviado ainda.")
                        continue

                    if len(ultimo_vetor_recebido) == 0:
                        print("Nenhum vetor foi recebido ainda.")
                        continue

                    plotar_comparacao(
                        ultimo_vetor_enviado,
                        ultimo_vetor_recebido
                    )

                elif choice == '4':

                    if len(ultimo_vetor_recebido) == 0:
                        print("Nenhum vetor recebido.")
                        continue

                    plotar_fft(
                        ultimo_vetor_recebido,
                        FS_ADC,
                        "FFT do sinal ADC"
                    )

                elif choice == '5':

                    if len(ultimo_vetor_enviado) == 0:
                        print("Nenhum vetor enviado.")
                        continue

                    if len(ultimo_vetor_recebido) == 0:
                        print("Nenhum vetor recebido.")
                        continue

                    comparar_fft(
                        ultimo_vetor_enviado,
                        ultimo_vetor_recebido,
                        FS_ADC
                    )



                elif choice == '6':

                    try:

                        f = float(input("Frequencia da onda (Hz): "))

                        n = int(input("Numero de amostras por ciclo: "))

                        bits = int(input("Resolucao do DAC (ex: 12): "))

                        amp = float(input("Amplitude normalizada (0 a 1): "))

                        vetor, fs = gerar_vetor_dac_com_harmonicas(

                            f,

                            n,

                            bits,

                            amp

                        )

                        ultimo_vetor_enviado = vetor.copy()

                        pasta_destino = r"C:\Users\Fernandes\Desktop\Trabalho Gulherme\DAC_ADC_EX\dac_adc_ex\utils"

                        caminho_completo = os.path.join(

                            pasta_destino,

                            "dac_buffer_values.c"

                        )

                        salvar_vetor_em_arquivo_c(

                            caminho_completo,

                            vetor,

                            f,

                            n,

                            bits,

                            amp,

                            fs

                        )

                        print(f"\nEnviando {len(vetor)} amostras...")

                        for val in vetor:
                            packet = struct.pack(

                                '<Bhh',

                                CMD_RECEIVE_INT,

                                2,

                                val

                            )

                            ser.write(packet)

                        print("Envio concluido.")

                        print("Harmonicas adicionadas:")

                        print("3ª = 15%")

                        print("5ª = 5%")

                        print("7ª = 3%")


                    except Exception as e:

                        print(f"Erro: {e}")

                # ==================================================
                # SAIR
                # ==================================================
                elif choice == '0':

                    print("Encerrando...")
                    break

                else:
                    print("Opcao invalida.")

    except serial.SerialException as e:

        print(f"Erro na porta serial: {e}")


if __name__ == "__main__":
    main()
