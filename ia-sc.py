# %%
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.multiclass import OneVsRestClassifier
import pickle

# Função para normalizar o texto
def normalizar_texto(texto):
    return texto.strip().lower()

# Carregar o dataset
dataset = pd.read_csv('problemas_combinados_2.csv', sep=',')

# Verificar as primeiras linhas do dataset
print("Primeiras linhas do dataset original:")
print(dataset.head())

# Unificar as colunas de quilometragem em uma única coluna
dataset_melted = pd.melt(
    dataset,
    id_vars=['Problema', 'Possíveis causas'],
    value_vars=['20.000km', '50.000km', '100.000km+'],
    var_name='Quilometragem',
    value_name='Probabilidade'
)

# Manter apenas as linhas com 'Probabilidade' > 0
dataset_melted = dataset_melted[dataset_melted['Probabilidade'] > 0]

# Normalizar os textos
dataset_melted['Problema'] = dataset_melted['Problema'].apply(normalizar_texto)
dataset_melted['Quilometragem'] = dataset_melted['Quilometragem'].apply(normalizar_texto)
dataset_melted['Possíveis causas'] = dataset_melted['Possíveis causas'].apply(
    lambda x: [normalizar_texto(causa) for causa in x.split(', ')]
)

# Combinar 'Problema' e 'Quilometragem' em uma única coluna de texto
dataset_melted['Entrada'] = dataset_melted['Problema'] + ' ' + dataset_melted['Quilometragem']

# Vetorizar a entrada usando TF-IDF com n-grams e ajustes
vectorizer = TfidfVectorizer(
    ngram_range=(1, 2),
    min_df=1,
    max_df=0.8,
    strip_accents='unicode',
    lowercase=True
)
X = vectorizer.fit_transform(dataset_melted['Entrada'])

# Binarizar 'Possíveis causas' para classificação multilabel
mlb = MultiLabelBinarizer()
y = mlb.fit_transform(dataset_melted['Possíveis causas'])

# Verificar a distribuição das classes
print("\nDistribuição das classes após binarização:")
print(pd.DataFrame(y, columns=mlb.classes_).sum())

# Dividir os dados em conjuntos de treinamento e teste
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Inicializar o modelo com OneVsRestClassifier e LogisticRegression com class_weight='balanced'
model = OneVsRestClassifier(
    LogisticRegression(max_iter=2000, solver='liblinear', class_weight='balanced')
)

# Treinar o modelo
model.fit(X_train, y_train)

# Fazer previsões no conjunto de teste
y_pred = model.predict(X_test)

# Avaliar o modelo
print("\nRelatório de Classificação:")
print(classification_report(y_test, y_pred, target_names=mlb.classes_))

# Salvar o modelo, o vetorizador e o binarizador em um arquivo pickle
with open('modelo_causas_aprimorado.pkl', 'wb') as f:
    pickle.dump({
        'model': model,
        'vectorizer': vectorizer,
        'mlb': mlb
    }, f)

print("Modelo aprimorado salvo como 'modelo_causas_aprimorado.pkl'")