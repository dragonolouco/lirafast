# Geração estrutural de objetos e mapas

Este protótipo demonstra a ideia de transformar uma estrutura em um objeto visual sem abrir Blender ou outro programa 3D.

O script [`obj_render.py`](obj_render.py) faz três coisas:

1. lê um arquivo OBJ;
2. calcula a estrutura geométrica e renderiza uma imagem PNG;
3. gera objetos novos a partir de parâmetros, como um cubo ou um mapa de altura.

## Renderizar um OBJ existente

```bash
python obj_render.py render \
  examples/models/nika_hair_v2.obj \
  examples/rendered/nika_hair_v2.png
```

O parser suporta vértices, objetos, faces triangulares e faces poligonais, convertendo polígonos em triângulos. A imagem é renderizada com uma câmera 3D simples e `matplotlib`.

## Criar um objeto procedural

```bash
python obj_render.py cube \
  examples/generated/cube.obj \
  examples/generated/cube.png \
  --size 2
```

## Criar um mapa procedural

```bash
python obj_render.py heightmap \
  examples/generated/heightmap.obj \
  examples/generated/heightmap.png \
  --rows 64 \
  --cols 64
```

O mapa não é armazenado como uma lista de respostas. Ele é reconstruído por uma regra:

```text
z = 0.18 * sin(x * 5) * cos(y * 4)
```

Essa é a mesma ideia do LiraFast aplicada à geometria:

```text
parâmetros + primitivas + regra
→ vértices e faces
→ malha OBJ
→ renderização PNG
```

## Exemplo real anexado

O modelo `nika_hair_v2.obj` possui aproximadamente 28.300 vértices, 28.246 faces e 5 objetos. Ele serve como um teste real de leitura e renderização, mas ainda é uma malha pronta. A próxima etapa é guardar os parâmetros e regras que conseguem reconstruir variações do penteado, em vez de armazenar somente todos os vértices.

## Limites atuais

Este é um renderizador de protótipo, não um motor 3D completo. Ainda não inclui materiais, texturas, iluminação física, animação, rigging ou simulação de fios. O objetivo inicial é comprovar o ciclo estrutural em Python e criar uma base que depois possa ser acelerada com NumPy, Rust, C++ ou workers distribuídos.

A velocidade deve ser medida separando:

- leitura do arquivo;
- geração da malha;
- transformação geométrica;
- renderização;
- gravação da imagem.

## Próximo pipeline: foto para objeto 3D

A imagem multivista `white_views.png` representa o próximo estágio: várias vistas do mesmo objeto servem como evidência para reconstruir uma malha. O pipeline será separado em etapas verificáveis:

```text
fotos/vistas
  -> normalização e segmentação
  -> pontos, silhuetas e correspondências
  -> estimativa de profundidade/volume
  -> malha inicial
  -> reparo de buracos e redução de ruído
  -> OBJ/glTF
  -> renderização de conferência
```

O sistema não deve fingir que uma única foto contém toda a geometria. Vistas múltiplas, escala, iluminação e partes ocultas são incertezas explícitas. A malha recriada deve guardar também a origem, a confiança por região e uma imagem de comparação com as vistas de entrada.

Esse é um caso ideal para a arquitetura adaptativa: um componente aprendido pode extrair características e propor uma hipótese de forma; o motor geométrico executa transformações determinísticas; e o verificador compara silhuetas, medidas e renderizações antes de aceitar a reconstrução.
