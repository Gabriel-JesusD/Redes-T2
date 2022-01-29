import asyncio
from grader.tcputils import FLAGS_ACK, FLAGS_FIN, FLAGS_SYN, fix_checksum, make_header
from tcputils import *


class Servidor:
    def __init__(self, rede, porta):
        self.rede = rede
        self.porta = porta
        self.conexoes = {}
        self.callback = None
        self.rede.registrar_recebedor(self._rdt_rcv)

    def registrar_monitor_de_conexoes_aceitas(self, callback):
        """
        Usado pela camada de aplicação para registrar uma função para ser chamada
        sempre que uma nova conexão for aceita
        """
        self.callback = callback

    def _rdt_rcv(self, src_addr, dst_addr, segment):
        src_port, dst_port, seq_no, ack_no, \
            flags, window_size, checksum, urg_ptr = read_header(segment)

        if dst_port != self.porta:
            # Ignora segmentos que não são destinados à porta do nosso servidor
            return
        if not self.rede.ignore_checksum and calc_checksum(segment, src_addr, dst_addr) != 0:
            print('descartando segmento com checksum incorreto')
            return

        payload = segment[4*(flags>>12):]
        id_conexao = (src_addr, src_port, dst_addr, dst_port)

        if (flags & FLAGS_SYN) == FLAGS_SYN:
            # A flag SYN estar setada significa que é um cliente tentando estabelecer uma conexão nova
            # TODO: talvez você precise passar mais coisas para o construtor de conexão
            ack_no = seq_no + 1
            conexao = self.conexoes[id_conexao] = Conexao(self, id_conexao, seq_no, ack_no)
            # TODO: você precisa fazer o handshake aceitando a conexão. Escolha
            # se você acha melhor
            flags = FLAGS_SYN + FLAGS_ACK
            newSegment = fix_checksum(make_header(dst_port, src_port, seq_no, ack_no, flags), src_addr, dst_addr)
            self.rede.enviar(newSegment, src_addr)
            # fazer aqui mesmo ou dentro da classe Conexao.
            if self.callback:
                self.callback(conexao)
        elif id_conexao in self.conexoes:
            # Passa para a conexão adequada se ela já estiver estabelecida
            self.conexoes[id_conexao]._rdt_rcv(seq_no, ack_no, flags, payload)
        else:
            print('%s:%d -> %s:%d (pacote associado a conexão desconhecida)' %
                  (src_addr, src_port, dst_addr, dst_port))


class Conexao:
    def __init__(self, servidor, id_conexao, seq_no, ack_no):
        self.servidor = servidor
        self.id_conexao = id_conexao
        self.callback = None
        self.seq_no = seq_no
        self.ack_no = ack_no
        self.ack_client = ack_no
        self.seq_client = ack_no
        self.open = True
        self.timer = asyncio.get_event_loop().call_later(1, self._exemplo_timer)  # um timer pode ser criado assim; esta linha é só um exemplo e pode ser removida
        #self.timer.cancel()   # é possível cancelar o timer chamando esse método; esta linha é só um exemplo e pode ser removida

    def _exemplo_timer(self):
        # Esta função é só um exemplo e pode ser removida
        print('Este é um exemplo de como fazer um timer')

    def _rdt_rcv(self, seq_no, ack_no, flags, payload):
        # TODO: trate aqui o recebimento de segmentos provenientes da camada de rede.
        # Chame self.callback(self, dados) para passar dados para a camada de aplicação após
        # garantir que eles não sejam duplicados e que tenham sido recebidos em
        # ordem.
        # print('recebido payload: %r' % payload)

        print(f'seq_no = {seq_no}, self.ack_no = {self.ack_no}, ack_no = {ack_no}, self.seq_no = {self.seq_no}')
        if seq_no != self.ack_no or (not len(payload) and (flags & FLAGS_FIN) != FLAGS_FIN) or not self.open: return
        print('ENTREI AQUI EM ALGUM MOMENTO, ack_no, seq_no, pay', ack_no, seq_no, len(payload))
        src_addr, src_port, dst_addr, dst_port = self.id_conexao
        self.seq_no = self.ack_no
        self.ack_no += len(payload) 
        if (flags & FLAGS_FIN) == FLAGS_FIN:
            self.ack_no += 1
        self.ack_client = self.ack_no
        print('SAI DAQUI EM ALGUM MOMENTO, ack_no, seq_no', self.ack_no, self.seq_no)
        self.callback(self, payload) 
        flags = FLAGS_ACK
        newSegment = fix_checksum(make_header(dst_port, src_port, self.seq_no, self.ack_no, flags), src_addr, dst_addr)
        self.servidor.rede.enviar(newSegment,src_addr)
        if (flags & FLAGS_FIN) == FLAGS_FIN:
            self.fechar()
            return


    # Os métodos abaixo fazem parte da API

    def registrar_recebedor(self, callback):
        """
        Usado pela camada de aplicação para registrar uma função para ser chamada
        sempre que dados forem corretamente recebidos
        """
        self.callback = callback

    def enviar(self, dados):
        """
        Usado pela camada de aplicação para enviar dados
        """
        if not self.open: return
        src_addr, src_port, dst_addr, dst_port = self.id_conexao
        # TODO: implemente aqui o envio de dados.
        # Chame self.servidor.rede.enviar(segmento, dest_addr) para enviar o
        # segmento
        i = 0
        src_addr, src_port, dst_addr, dst_port = self.id_conexao
        print(f'TAMANHO DOS DADOS = {len(dados)}, SEQ_NO = {self.seq_no}, ACK_NO = {self.ack_no}, ACK_CLIENTE = {self.ack_client}')
        # seq_no = 
        while i < len(dados):
            payload = dados[i:i+MSS]
            flags = FLAGS_ACK
            # self._rdt_rcv(self.seq_no, self.ack_no, flags, payload)
            # seq_no = self.ack_client
            print(f'APOS ITERACAO, ack = {self.ack_client}, seq = {self.seq_client}')
            newSegment = fix_checksum(make_header(dst_port, src_port, self.seq_client, self.ack_client, flags) + payload, src_addr, dst_addr)
            self.seq_client += len(payload)
            # seq_no = self.ack_client
            # print(f'pld = {len(payload)} sq = {self.seq_no}')
            self.servidor.rede.enviar(newSegment,src_addr)
            i += MSS

        # self.ack_no += len(dados)
        print(f'SAINDO DO LOOP, ack = {self.ack_no}, seq = {self.seq_no}')
        # self.ack_no = self.seq_no
        # que você construir para a camada de rede.


    def fechar(self):
        """
        Usado pela camada de aplicação para fechar a conexão
        """
        print('got here as well')
        src_addr, src_port, dst_addr, dst_port = self.id_conexao
        # TODO: implemente aqui o fechamento de conexão
        self.callback(self,b'')
        flags = FLAGS_FIN
        newSegment = fix_checksum(make_header(dst_port, src_port, self.seq_no, self.ack_no, flags) , src_addr, dst_addr)
        self.servidor.rede.enviar(newSegment,src_addr)
        self.open = False
        pass
