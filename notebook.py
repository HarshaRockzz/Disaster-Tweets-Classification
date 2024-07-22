
# **1. Library Import**
"""

!pip install -q condacolab
import condacolab
condacolab.install()

!conda --version

!conda create --name mlops-tfx python==3.9.15

!conda activate mlops-tfx

!pip install jupyter scikit-learn tensorflow tfx==1.11.0 flask joblib

import os
import pandas as pd

import tensorflow as tf
import tensorflow_model_analysis as tfma

from tfx.components import CsvExampleGen, StatisticsGen, SchemaGen, ExampleValidator
from tfx.components import Transform, Trainer, Tuner, Evaluator, Pusher
from tfx.proto import example_gen_pb2, trainer_pb2, pusher_pb2
from tfx.orchestration.experimental.interactive.interactive_context import InteractiveContext
from tfx.dsl.components.common.resolver import Resolver
from tfx.dsl.input_resolution.strategies.latest_blessed_model_strategy import LatestBlessedModelStrategy
from tfx.types import Channel
from tfx.types.standard_artifacts import Model, ModelBlessing

"""# **2. Set Pipeline Variable**"""

PIPELINE_NAME = 'disaster-tweets-pipeline'
SCHEMA_PIPELINE_NAME = 'disaster-tweets-tfdv-schema'

PIPELINE_ROOT = os.path.join('pipelines', PIPELINE_NAME)
METADATA_PATH = os.path.join('metadata', PIPELINE_NAME, 'metadata.db')

SERVING_MODEL_DIR = os.path.join('serving_model', PIPELINE_NAME)

"""# **3. Data Loading**

## 3.1 Environment and Kaggle Credential

Set up the [Colab](https://colab.research.google.com) `operating system` environment with the `KAGGLE_USERNAME` variable and the `KAGGLE_KEY` variable to connect to the [Kaggle](https://kaggle.com) platform using [Kaggle's Beta API](https://www.kaggle.com/docs/api) Token.
"""

os.environ['KAGGLE_USERNAME'] = 'harsharockerzzzz'
os.environ['KAGGLE_KEY']      = 'b75c236a492526b84d0dc7517c37d48b'

"""## 3.2 Dataset Download

Download the dataset form Kaggle with the dataset file name, `train_data_cleaning.csv`. The dataset used in this project is the [NLP with Disaster Tweets](https://www.kaggle.com/datasets/vbmokin/nlp-with-disaster-tweets-cleaning-data) dataset in the form of a `.csv` ([Comma-separated Values](https://en.wikipedia.org/wiki/Comma-separated_values)) file.
"""

!kaggle datasets download -d vbmokin/nlp-with-disaster-tweets-cleaning-data -f train_data_cleaning.csv

"""## 3.3 Dataset Preparation"""

DATA_PATH = 'data'

df = pd.read_csv('train_data_cleaning.csv')
df = df.drop(['id', 'keyword', 'location'], axis=1)
df = df.rename(columns={'target': 'label'})

if not os.path.exists(DATA_PATH):
    os.makedirs(DATA_PATH)

df.to_csv(os.path.join(DATA_PATH, 'disaster_tweets.csv'), index=False)

df.head()

DATA_ROOT = 'data'

interactive_context = InteractiveContext(pipeline_root=PIPELINE_ROOT)

"""# **4. Data Ingestion**"""

output = example_gen_pb2.Output(
    split_config = example_gen_pb2.SplitConfig(splits=[
        example_gen_pb2.SplitConfig.Split(name='train', hash_buckets=9),
        example_gen_pb2.SplitConfig.Split(name='eval',  hash_buckets=1)
    ])
)

example_gen = CsvExampleGen(input_base=DATA_ROOT, output_config=output)

interactive_context.run(example_gen)

"""# **5. Data Validation**

## 5.1 Statistic Summary
"""

statistics_gen = StatisticsGen(
    examples = example_gen.outputs['examples']
)

interactive_context.run(statistics_gen)

interactive_context.show(statistics_gen.outputs['statistics'])

"""## 5.2 Data Schema"""

schema_gen = SchemaGen(
    statistics = statistics_gen.outputs['statistics']
)

interactive_context.run(schema_gen)

interactive_context.show(schema_gen.outputs['schema'])

"""## 5.3 Data Anomaly Identification"""

example_validator = ExampleValidator(
    statistics = statistics_gen.outputs['statistics'],
    schema     = schema_gen.outputs['schema']
)

interactive_context.run(example_validator)

interactive_context.show(example_validator.outputs['anomalies'])

"""# **6. Data Preprocessing**"""

TRANSFORM_MODULE_FILE = 'disaster_tweets_transform.py'

# Commented out IPython magic to ensure Python compatibility.
# %%writefile {TRANSFORM_MODULE_FILE}
# import tensorflow as tf
# 
# LABEL_KEY   = "label"
# FEATURE_KEY = "text"
# 
# # Renaming transformed features
# def transformed_name(key):
#     return key + "_xf"
# 
# # Preprocess input features into transformed features
# def preprocessing_fn(inputs):
#     """
#     inputs:  map from feature keys to raw features
#     outputs: map from feature keys to transformed features
#     """
# 
#     outputs = {}
#     outputs[transformed_name(FEATURE_KEY)] = tf.strings.lower(inputs[FEATURE_KEY])
#     outputs[transformed_name(LABEL_KEY)]   = tf.cast(inputs[LABEL_KEY], tf.int64)
#     
#     return outputs

transform = Transform(
    examples    = example_gen.outputs['examples'],
    schema      = schema_gen.outputs['schema'],
    module_file = os.path.abspath(TRANSFORM_MODULE_FILE)
)

interactive_context.run(transform)

"""# **7. Hyperparameter Tuning**

References

- [Keras - KerasTuner](https://keras.io/keras_tuner)  
- [TensorFlow - TFX Tuner](https://www.tensorflow.org/tfx/guide/tuner)  
- [Dicoding - Pembuatan Komponen Tuner](https://www.dicoding.com/academies/443/discussions/211900)
"""

TUNER_MODULE_FILE = 'disaster_tweets_tuner.py'

# Commented out IPython magic to ensure Python compatibility.
# %%writefile {TUNER_MODULE_FILE}
# import os
# import tensorflow as tf
# import tensorflow_transform as tft
# import keras_tuner as kt
# from tensorflow.keras import layers
# from tfx.components.trainer.fn_args_utils import FnArgs
# from keras_tuner.engine import base_tuner
# from typing import NamedTuple, Dict, Text, Any
# 
# LABEL_KEY   = 'label'
# FEATURE_KEY = 'text'
# 
# def transformed_name(key):
#     """Renaming transformed features"""
#     return key + "_xf"
# 
# def gzip_reader_fn(filenames):
#     """Loads compressed data"""
#     return tf.data.TFRecordDataset(filenames, compression_type='GZIP')
# 
# def input_fn(file_pattern, tf_transform_output, num_epochs, batch_size=64) -> tf.data.Dataset:
#     """Get post_tranform feature & create batches of data"""
#     
#     # Get post_transform feature spec
#     transform_feature_spec = (
#         tf_transform_output.transformed_feature_spec().copy()
#     )
#     
#     # create batches of data
#     dataset = tf.data.experimental.make_batched_features_dataset(
#         file_pattern = file_pattern,
#         batch_size   = batch_size,
#         features     = transform_feature_spec,
#         reader       = gzip_reader_fn,
#         num_epochs   = num_epochs,
#         label_key    = transformed_name(LABEL_KEY)
#     )
# 
#     return dataset
# 
# # Vocabulary size and number of words in a sequence.
# VOCAB_SIZE      = 10000
# SEQUENCE_LENGTH = 100
# 
# vectorize_layer = layers.TextVectorization(
#     standardize            = 'lower_and_strip_punctuation',
#     max_tokens             = VOCAB_SIZE,
#     output_mode            = 'int',
#     output_sequence_length = SEQUENCE_LENGTH
# )
# 
# def model_builder(hp):
#     """Build keras tuner model"""
#     embedding_dim = hp.Int('embedding_dim', min_value=16, max_value=128, step=16)
#     lstm_units    = hp.Int('lstm_units', min_value=16, max_value=128, step=16)
#     num_layers    = hp.Choice('num_layers', values=[1, 2, 3])
#     dense_units   = hp.Int('dense_units', min_value=16, max_value=128, step=16)
#     dropout_rate = hp.Float('dropout_rate', min_value=0.1, max_value=0.5, step=0.1)
#     learning_rate = hp.Choice('learning_rate', values=[1e-2, 1e-3, 1e-4])
#     
#     inputs = tf.keras.Input(shape=(1,), name=transformed_name(FEATURE_KEY), dtype=tf.string)
#     
#     reshaped_narrative = tf.reshape(inputs, [-1])
#     x = vectorize_layer(reshaped_narrative)
#     x = layers.Embedding(VOCAB_SIZE, embedding_dim, name='embedding')(x)
#     x = layers.Bidirectional(layers.LSTM(lstm_units))(x)
#     for _ in range(num_layers):
#         x = layers.Dense(dense_units, activation='relu')(x)
#     x = layers.Dropout(dropout_rate)(x)
#     outputs = layers.Dense(1, activation='sigmoid')(x)
#     
#     model = tf.keras.Model(inputs = inputs, outputs = outputs)
#     model.compile(
#         loss      = tf.keras.losses.BinaryCrossentropy(from_logits=True),
#         optimizer = tf.keras.optimizers.Adam(learning_rate),
#         metrics   = [tf.keras.metrics.BinaryAccuracy()]
#     )
#     
#     model.summary()
#     return model
# 
# TunerFnResult = NamedTuple('TunerFnResult', [
#     ('tuner', base_tuner.BaseTuner),
#     ('fit_kwargs', Dict[Text, Any]),
# ])
# 
# early_stop_callback = tf.keras.callbacks.EarlyStopping(
#     monitor  = 'val_binary_accuracy',
#     mode     = 'max',
#     verbose  = 1,
#     patience = 10
# )
# 
# def tuner_fn(fn_args: FnArgs) -> None:
#     # Load the transform output
#     tf_transform_output = tft.TFTransformOutput(fn_args.transform_graph_path)
#     
#     # Create batches of data
#     train_set = input_fn(fn_args.train_files[0], tf_transform_output, 10)
#     val_set   = input_fn(fn_args.eval_files[0],  tf_transform_output, 10)
# 
#     vectorize_layer.adapt(
#         [j[0].numpy()[0] for j in [
#             i[0][transformed_name(FEATURE_KEY)]
#                 for i in list(train_set)
#         ]]
#     )
#     
#     # Build the model tuner
#     model_tuner = kt.Hyperband(
#         hypermodel   = lambda hp: model_builder(hp),
#         objective    = kt.Objective('val_binary_accuracy', direction='max'),
#         max_epochs   = 10,
#         factor       = 3,
#         directory    = fn_args.working_dir,
#         project_name = 'disaster_tweets_kt'
#     )
# 
#     return TunerFnResult(
#         tuner      = model_tuner,
#         fit_kwargs = {
#             'callbacks'        : [early_stop_callback],
#             'x'                : train_set,
#             'validation_data'  : val_set,
#             'steps_per_epoch'  : fn_args.train_steps,
#             'validation_steps' : fn_args.eval_steps
#         }
#     )

tuner = Tuner(
    module_file     = os.path.abspath(TUNER_MODULE_FILE),
    examples        = transform.outputs['transformed_examples'],
    transform_graph = transform.outputs['transform_graph'],
    schema          = schema_gen.outputs['schema'],
    train_args      = trainer_pb2.TrainArgs(splits=['train']),
    eval_args       = trainer_pb2.EvalArgs(splits=['eval'])
)

interactive_context.run(tuner)

"""# **8. Model Development**"""

TRAINER_MODULE_FILE = 'disaster_tweets_trainer.py'

# Commented out IPython magic to ensure Python compatibility.
# %%writefile {TRAINER_MODULE_FILE}
# import os
# import tensorflow as tf
# import tensorflow_transform as tft
# from tensorflow.keras import layers
# from tfx.components.trainer.fn_args_utils import FnArgs
# 
# LABEL_KEY   = 'label'
# FEATURE_KEY = 'text'
# 
# def transformed_name(key):
#     """Renaming transformed features"""
#     return key + "_xf"
# 
# def gzip_reader_fn(filenames):
#     """Loads compressed data"""
#     return tf.data.TFRecordDataset(filenames, compression_type='GZIP')
# 
# def input_fn(file_pattern, tf_transform_output, num_epochs, batch_size=64) -> tf.data.Dataset:
#     """Get post_tranform feature & create batches of data"""
#     
#     # Get post_transform feature spec
#     transform_feature_spec = (
#         tf_transform_output.transformed_feature_spec().copy()
#     )
#     
#     # Create batches of data
#     dataset = tf.data.experimental.make_batched_features_dataset(
#         file_pattern = file_pattern,
#         batch_size   = batch_size,
#         features     = transform_feature_spec,
#         reader       = gzip_reader_fn,
#         num_epochs   = num_epochs,
#         label_key    = transformed_name(LABEL_KEY)
#     )
# 
#     return dataset
# 
# # Vocabulary size and number of words in a sequence
# VOCAB_SIZE      = 10000
# SEQUENCE_LENGTH = 100
# embedding_dim   = 16
# 
# vectorize_layer = layers.TextVectorization(
#     standardize            = 'lower_and_strip_punctuation',
#     max_tokens             = VOCAB_SIZE,
#     output_mode            = 'int',
#     output_sequence_length = SEQUENCE_LENGTH
# )
# 
# def model_builder(hp):
#     """Build machine learning model"""
#     inputs = tf.keras.Input(shape=(1,), name=transformed_name(FEATURE_KEY), dtype=tf.string)
#     
#     reshaped_narrative = tf.reshape(inputs, [-1])
#     x = vectorize_layer(reshaped_narrative)
#     x = layers.Embedding(VOCAB_SIZE, hp['embedding_dim'], name='embedding')(x)
#     x = layers.Bidirectional(layers.LSTM(hp['lstm_units']))(x)
#     for _ in range(hp['num_layers']):
#         x = layers.Dense(hp['dense_units'], activation='relu')(x)
#     x = layers.Dropout(hp['dropout_rate'])(x)
#     outputs = layers.Dense(1, activation='sigmoid')(x)
#     
#     model = tf.keras.Model(inputs = inputs, outputs = outputs)
#     model.compile(
#         loss      = tf.keras.losses.BinaryCrossentropy(from_logits=True),
#         optimizer = tf.keras.optimizers.Adam(hp['learning_rate']),
#         metrics   = [tf.keras.metrics.BinaryAccuracy()]
#     )
#     
#     model.summary()
#     return model
# 
# def _get_serve_tf_examples_fn(model, tf_transform_output):
#     model.tft_layer = tf_transform_output.transform_features_layer()
#     
#     @tf.function
#     def serve_tf_examples_fn(serialized_tf_examples):
#         feature_spec = tf_transform_output.raw_feature_spec()
#         feature_spec.pop(LABEL_KEY)
# 
#         parsed_features      = tf.io.parse_example(serialized_tf_examples, feature_spec)
#         transformed_features = model.tft_layer(parsed_features)
#         
#         # get predictions using the transformed features
#         return model(transformed_features)
#         
#     return serve_tf_examples_fn
#     
# def run_fn(fn_args: FnArgs) -> None:
#     log_dir = os.path.join(os.path.dirname(fn_args.serving_model_dir), 'logs')
#     hp      = fn_args.hyperparameters['values']
#     
#     tensorboard_callback = tf.keras.callbacks.TensorBoard(
#         log_dir = log_dir, update_freq='batch'
#     )
#     
#     early_stop_callback = tf.keras.callbacks.EarlyStopping(
#         monitor  = 'val_binary_accuracy',
#         mode     = 'max',
#         verbose  = 1,
#         patience = 10
#     )
# 
#     model_checkpoint_callback = tf.keras.callbacks.ModelCheckpoint(
#         fn_args.serving_model_dir,
#         monitor        = 'val_binary_accuracy',
#         mode           = 'max',
#         verbose        = 1,
#         save_best_only = True
#     )
# 
#     callbacks = [
#         tensorboard_callback,
#         early_stop_callback,
#         model_checkpoint_callback
#     ]
#     
#     # Load the transform output
#     tf_transform_output = tft.TFTransformOutput(fn_args.transform_graph_path)
#     
#     # Create batches of data
#     train_set = input_fn(fn_args.train_files, tf_transform_output, hp['tuner/epochs'])
#     val_set   = input_fn(fn_args.eval_files,  tf_transform_output, hp['tuner/epochs'])
# 
#     vectorize_layer.adapt(
#         [j[0].numpy()[0] for j in [
#             i[0][transformed_name(FEATURE_KEY)]
#                 for i in list(train_set)
#         ]]
#     )
#     
#     # Build the model
#     model = model_builder(hp)
#     
#     # Train the model
#     model.fit(
#         x                = train_set,
#         validation_data  = val_set,
#         callbacks        = callbacks,
#         steps_per_epoch  = fn_args.train_steps,
#         validation_steps = fn_args.eval_steps,
#         epochs           = hp['tuner/epochs']
#     )
# 
#     signatures = {
#         'serving_default': _get_serve_tf_examples_fn(
#             model, tf_transform_output
#         ).get_concrete_function(
#             tf.TensorSpec(
#                 shape = [None],
#                 dtype = tf.string,
#                 name  = 'examples'
#             )
#         )
#     }
# 
#     model.save(
#         fn_args.serving_model_dir,
#         save_format = 'tf',
#         signatures  = signatures
#     )

trainer = Trainer(
    module_file     = os.path.abspath(TRAINER_MODULE_FILE),
    examples        = transform.outputs['transformed_examples'],
    transform_graph = transform.outputs['transform_graph'],
    schema          = schema_gen.outputs['schema'],
    hyperparameters = tuner.outputs['best_hyperparameters'],
    train_args      = trainer_pb2.TrainArgs(splits=['train']),
    eval_args       = trainer_pb2.EvalArgs(splits=['eval'])
)

interactive_context.run(trainer)

"""# **9. Model Analysis and Validation**

## 9.1 Resolver
"""

model_resolver = Resolver(
    strategy_class = LatestBlessedModelStrategy,
    model          = Channel(type=Model),
    model_blessing = Channel(type=ModelBlessing)
).with_id('Latest_blessed_model_resolver')

interactive_context.run(model_resolver)

"""## 9.2 Evaluator"""

eval_config = tfma.EvalConfig(
    model_specs   = [tfma.ModelSpec(label_key = 'label')],
    slicing_specs = [tfma.SlicingSpec()],
    metrics_specs = [
        tfma.MetricsSpec(metrics=[
            tfma.MetricConfig(class_name = 'ExampleCount'),
            tfma.MetricConfig(class_name = 'AUC'),
            tfma.MetricConfig(class_name = 'FalsePositives'),
            tfma.MetricConfig(class_name = 'TruePositives'),
            tfma.MetricConfig(class_name = 'FalseNegatives'),
            tfma.MetricConfig(class_name = 'TrueNegatives'),
            tfma.MetricConfig(class_name = 'BinaryAccuracy',
                threshold=tfma.MetricThreshold(
                    value_threshold = tfma.GenericValueThreshold(
                        lower_bound = {'value': 0.5}
                    ),
                    change_threshold = tfma.GenericChangeThreshold(
                        direction = tfma.MetricDirection.HIGHER_IS_BETTER,
                        absolute  = {'value': 0.0001}
                    )
                )
            )
        ])
    ]
)

evaluator = Evaluator(
    examples       = example_gen.outputs['examples'],
    model          = trainer.outputs['model'],
    baseline_model = model_resolver.outputs['model'],
    eval_config    = eval_config
)

interactive_context.run(evaluator)

eval_result = evaluator.outputs['evaluation'].get()[0].uri
tfma_result = tfma.load_eval_result(eval_result)
tfma.view.render_slicing_metrics(tfma_result)
tfma.addons.fairness.view.widget_view.render_fairness_indicator(tfma_result)

"""## **10. Model Deployment and Export**"""

from tfx.components import Pusher
from tfx.proto import pusher_pb2

pusher = Pusher(
    model            = trainer.outputs['model'],
    model_blessing   = evaluator.outputs['blessing'],
    push_destination = pusher_pb2.PushDestination(
        filesystem = pusher_pb2.PushDestination.Filesystem(
            base_directory = 'serving_model_dir/disaster-tweets-model')
    )
)

interactive_context.run(pusher)

!zip -r pipelines.zip pipelines/
!zip -r serving_model_dir.zip serving_model_dir/
!pip freeze > requirements.txt

