[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/ItUD98Nn)

# Multipoint Messaging with Ordering

Sistema de mensagens multiponto com consistência de réplicas garantida por ordenação total das mensagens.

## Modelo de consistência

O sistema adota **consistência sequencial**: todas as réplicas (peers) recebem e entregam as mensagens na mesma ordem global, independentemente da ordem de envio ou da latência da rede. Isso é implementado por um sequenciador centralizado (Group Manager), que atribui um número de sequência único e crescente a cada mensagem antes de reencaminhá-la aos peers.

Consistência causal ou eventual seria insuficiente, pois réplicas poderiam divergir na ordem das operações. Consistência estrita exigiria sincronização de relógios físicos, impraticável em ambiente distribuído. A consistência sequencial é o modelo mais forte viável e suficiente para o requisito de ordenação total.

## Arquitetura

```
[Peer] ──TCP──► [Group Manager] ──UDP──► [todos os Peers]
                      │
                 atribui seq_num
                 e reencaminha
                      │
               [Naming Service]  ← peers e GM se registram/descobrem aqui
```

| Componente | Protocolo | Função |
|---|---|---|
| `naming_service.py` | TCP/ZMQ REQ-REP | Registro e descoberta de endereços |
| `group_manager.py` | TCP (recebe) + UDP (envia) | Sequenciador central; mantém histórico |
| `peer.py` | TCP (envia) + UDP (recebe) | Réplica; entrega mensagens em ordem via hold-back queue |

O peer mantém uma **hold-back queue**: mensagens fora de ordem ficam em buffer até que todas as anteriores tenham sido entregues, garantindo ordenação total na entrega.

## Módulos

### Naming Service (`naming_service.py`)

Serviço de diretório centralizado baseado em ZMQ REQ-REP. Mantém um registro de nome → endereço (`ip:porta`) e um registro de nome → tipo, permitindo que processos se registrem e sejam descobertos por tipo. Operações disponíveis: `bind`, `lookup`, `unbind`, `register` e `discover`.

O cliente do serviço está em `naming_client.py`, que encapsula as chamadas ZMQ e é usado tanto pelo Group Manager quanto pelos peers.

### Group Manager (`group_manager.py`)

Sequenciador central do sistema. Recebe mensagens dos peers via TCP, atribui um número de sequência global (`seq_num`) incrementado monotonicamente e reencaminha a mensagem serializada via UDP para todos os peers registrados no Naming Service. Mantém o histórico completo de mensagens, permitindo que peers recém-conectados solicitem o estado atual via operação `history`.

É o único componente que atribui números de sequência, o que garante que todos os peers observem a mesma ordem total de mensagens.

### Peer (`peer.py`)

Réplica da aplicação. Envia mensagens ao Group Manager via TCP e recebe as mensagens sequenciadas via UDP. Implementa uma **hold-back queue**: mensagens que chegam fora de ordem são mantidas em buffer e entregues somente quando todos os `seq_num` anteriores já foram recebidos, garantindo entrega ordenada mesmo sob reordenação de pacotes UDP.

## Fluxo de entrega de uma mensagem

1. O peer remetente envia a mensagem ao Group Manager via TCP, incluindo seu IP e porta UDP de retorno.
2. O Group Manager recebe a mensagem, incrementa o contador global e atribui o próximo `seq_num`.
3. O Group Manager consulta o Naming Service para obter os endereços de todos os peers registrados.
4. A mensagem sequenciada é enviada via UDP a cada peer (incluindo o remetente).
5. Cada peer recebe a mensagem e a insere na hold-back queue indexada por `seq_num`.
6. O peer entrega à aplicação todas as mensagens consecutivas a partir do próximo `seq_num` esperado, segurando as demais até que os gaps sejam preenchidos.
