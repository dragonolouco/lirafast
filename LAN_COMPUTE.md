# LiraFast LAN Compute MVP

Este MVP permite usar computadores e celulares compatíveis com Python como **workers de cálculo na mesma rede Wi‑Fi**. O coordenador divide uma faixa em lotes, envia cada lote por HTTP, recebe resultados e verifica se todos os intervalos foram cobertos exatamente uma vez.

## O que ele faz

- worker HTTP leve, somente com a biblioteca padrão do Python;
- compatível com Linux, macOS, Windows e Android via Termux/Pydroid;
- kernels inteiros determinísticos: `sum_squares` e `sum_cubes`;
- divisão em lotes e execução concorrente;
- verificação de operação, início/fim, cobertura e soma final;
- token opcional para evitar chamadas acidentais na rede local;
- benchmark local versus distribuído.

## Executar um worker no computador

```bash
cd lirafast
python lan_compute.py worker --host 0.0.0.0 --port 8765
```

Descubra o IP local da máquina (`ip addr`, `ifconfig` ou equivalente). Teste:

```bash
curl http://IP_DA_MAQUINA:8765/health
```

## Executar no celular Android

Uma opção simples de laboratório é instalar Termux, instalar Python e executar o mesmo comando:

```bash
pkg update
pkg install python
python lan_compute.py worker --host 0.0.0.0 --port 8765
```

O celular e o coordenador precisam estar na mesma rede Wi‑Fi. A rede deve permitir comunicação entre dispositivos; algumas redes de convidados bloqueiam isso.

## Distribuir um cálculo

No computador coordenador:

```bash
python lan_compute.py coordinator \
  --workers http://IP_DO_CELULAR:8765 http://IP_DO_PC:8765 \
  --operation sum_squares \
  --start 0 \
  --end 1000000 \
  --chunk-size 100000
```

Para proteger a sessão com um token:

```bash
export LIRAFAST_TOKEN='troque-este-token'
python lan_compute.py worker --host 0.0.0.0 --port 8765
python lan_compute.py coordinator --workers http://IP_DO_CELULAR:8765 --end 1000000
```

## Protocolo mínimo

`GET /health` retorna capacidade básica do worker.

`POST /compute` recebe:

```json
{"operation":"sum_squares","start":0,"end":100000}
```

E retorna um resultado com operação, intervalo, valor, número de iterações e tempo local. O intervalo é semiaberto: `[start, end)`.

## Verificação

O coordenador verifica:

1. se cada worker devolveu a operação solicitada;
2. se o intervalo devolvido corresponde ao lote enviado;
3. se não existem lacunas ou sobreposições;
4. se o número de iterações coincide com o intervalo;
5. se o resultado distribuído coincide com uma execução local de referência no benchmark.

## O que ainda não é

Este MVP **não é um computador quântico** e não promete superar qualquer calculadora ou computador sem medição. Ele é uma infraestrutura de paralelismo cooperativo. A velocidade real depende de CPU, aquecimento, tamanho dos lotes, latência Wi‑Fi, energia, temperatura, sistema operacional e custo de serialização.

A ideia de “parecido com quântica” deve ser traduzida em mecanismos testáveis: representação compacta, decomposição de estados, paralelismo, poda de busca, memoização e algoritmos matemáticos melhores. Paralelizar um cálculo que possui uma fórmula fechada pode ser mais lento do que usar essa fórmula; por isso, cada kernel precisa de benchmark e verificação próprios.

## Próximos passos

1. adicionar descoberta de workers por mDNS/UDP, sem confiar automaticamente em qualquer dispositivo;
2. criar fila persistente e retomada de lotes interrompidos;
3. adicionar kernels de multiplicação modular, fatoração experimental e álgebra vetorial;
4. criar um app Expo para registrar o celular, mostrar bateria/temperatura e iniciar/parar o worker;
5. migrar kernels críticos para Rust/C++/NDK quando o benchmark justificar;
6. comparar execução local, um celular e vários workers com os mesmos casos;
7. adicionar limites de energia, tamanho, autenticação e cancelamento.
