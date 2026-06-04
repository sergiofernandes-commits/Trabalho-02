//
// Included Files
//
#include "driverlib.h"
#include "device.h"
#include "board.h"
#include "scicomm.h"

volatile Protocol_Header_t g_prot_header = {CMD_NONE,0};
#define TAM_BUFFER 200

#define TAM_BUFFER_DAC 200
#define TAM_BUFFER_ADC 200

extern uint16_t dac_buffer[];
volatile uint16_t adc_buffer[TAM_BUFFER_ADC];
volatile float gain = 1.0f;

volatile int g_dado[TAM_BUFFER];
volatile uint16_t g_indice = 0;
volatile uint16_t g_send = 0;

//
// Fun��o Principal
//
void main(void)
{
    // Inicializa��o do dispositivo
    Device_init();
    Interrupt_initModule();
    Interrupt_initVectorTable();
    Board_init();

    // Habilita interrup��es globais e de tempo real
    EINT;
    ERTM;

    while (1)
    {
        if (g_prot_header.cmd != CMD_NONE)
        {
            switch (g_prot_header.cmd)
            {
                case CMD_RECEIVE_INT:
                    if(g_indice < TAM_BUFFER)
                        {
                            g_dado[g_indice++] = protocolReceiveInt(SCI0_BASE);
                            if(g_indice >= TAM_BUFFER)
                            {
                                g_indice = 0;
                            }
                        }
                        break;

                case CMD_SEND_INT:
                    {
                        uint16_t i;

                        if (g_send<TAM_BUFFER) 
                        {
                        
                        protocolSendInt(SCI0_BASE, adc_buffer[g_send]);
                        g_send++;
                        if (g_send>=199)
                        {
                            g_send = 0;
                        }
                        }
                            
                        
                        break;
                    }
            
            }

            // Limpa status de interrup��o e reseta comando
            SCI_clearInterruptStatus(SCI0_BASE, SCI_INT_RXFF);
            g_prot_header.cmd = CMD_NONE;
        }
    }
}

//
// Rotina de Interrup��o da SCI (Recep��o)
//
__interrupt void INT_SCI0_RX_ISR(void)
{
    uint16_t header[PROTOCOL_HEADER_SIZE];
    uint16_t cmd;

    SCI_readCharArray(SCI0_BASE, header, PROTOCOL_HEADER_SIZE);
    cmd = header[0];
    g_prot_header.data_len = header[1] | (header[2] << 8);
    g_prot_header.cmd = (cmd < CMD_COUNT)? (SCI_Command_e)cmd : CMD_NONE;

    Interrupt_clearACKGroup(INT_SCI0_RX_INTERRUPT_ACK_GROUP);
}




volatile uint32_t testeDAC = 0;
__interrupt void INT_myCPUTIMER1_ISR(void)
{
    testeDAC++;
    static uint16_t cnt_dac = 0;
    DAC_setShadowValue(DAC0_BASE, (uint16_t) (gain*g_dado[cnt_dac]));
    cnt_dac = (cnt_dac+1)%TAM_BUFFER_DAC;

}

volatile uint32_t testeADC = 0;
__interrupt void INT_ADC0_1_ISR(void)
{
    testeADC++;
    static uint16_t valor =0;
    valor = (valor+1)%TAM_BUFFER_ADC;
    adc_buffer[valor] = ADC_readResult(ADC0_RESULT_BASE, ADC0_SOC0);
    ADC_clearInterruptStatus(ADC0_BASE, ADC_INT_NUMBER1);
    Interrupt_clearACKGroup(INT_ADC0_1_INTERRUPT_ACK_GROUP);

}