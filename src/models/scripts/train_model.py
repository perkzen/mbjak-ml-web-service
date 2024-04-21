import os

import dagshub
from mlflow import MlflowClient
from sklearn.preprocessing import MinMaxScaler
import dagshub.auth as dh_auth

from src.config import settings
from src.models import create_test_train_split
from src.models.helpers import load_bike_station_dataset
from src.models.model import train_model, build_model, prepare_model_data
from src.utils.decorators import execution_timer
import mlflow
from mlflow.keras import log_model as log_keras_model
from mlflow.sklearn import log_model as log_sklearn_model
from mlflow.models import infer_signature


def train_model_pipeline(station_number: int) -> None:
    mlflow.start_run(run_name="mbajk_station_" + str(station_number))

    dataset = load_bike_station_dataset(str(station_number), "train")
    scaler = MinMaxScaler()

    train_data, test_data = create_test_train_split(str(station_number))

    X_train, y_train, X_test, y_test = prepare_model_data(dataset=dataset, scaler=scaler, train_data=train_data,
                                                          test_data=test_data)

    model = train_model(X_train=X_train, y_train=y_train, X_test=X_test, y_test=y_test, build_model_fn=build_model,
                        epochs=10, batch_size=32,
                        verbose=0)

    mlflow.log_param("epochs", 10)
    mlflow.log_param("batch_size", 32)
    mlflow.log_param("dataset_size", len(dataset))

    client = MlflowClient()

    # save model
    model_ = log_keras_model(model=model,
                             artifact_path=f"models/station_{station_number}",
                             signature=infer_signature(X_test, model.predict(X_test)),
                             registered_model_name="mbajk_station_" + str(station_number))

    mv = client.create_model_version(name="mbajk_station_" + str(station_number), source=model_.model_uri,
                                     run_id=model_.run_id)
    client.transition_model_version_stage("mbajk_station_" + str(station_number), mv.version, "staging")

    # save scaler
    scaler_meta = {"feature_range": scaler.feature_range}
    scaler = log_sklearn_model(
        sk_model=scaler,
        artifact_path=f"scalers/station_{station_number}",
        registered_model_name="mbajk_station_" + str(station_number) + "_scaler",
        metadata=scaler_meta
    )

    sv = client.create_model_version(name="mbajk_station_" + str(station_number) + "_scaler", source=scaler.model_uri,
                                     run_id=scaler.run_id)
    # set stage
    client.transition_model_version_stage("mbajk_station_" + str(station_number) + "_scaler", sv.version, "staging")

    print(f"[Train Model] - Model for station {station_number} has been trained and saved")

    mlflow.end_run()


@execution_timer("Train Model")
def main() -> None:
    dir_path = "data/processed"
    station_numbers = [int(folder) for folder in os.listdir(dir_path) if os.path.isdir(os.path.join(dir_path, folder))]

    dh_auth.add_app_token(token=settings.dagshub_user_token)
    dagshub.init("mbajk-ml-web-service", "perkzen", mlflow=True)
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    #
    # with Pool(processes=os.cpu_count()) as pool:
    #     pool.map(train_model_pipeline, station_numbers)

    for station_number in station_numbers:
        train_model_pipeline(station_number)


if __name__ == "__main__":
    main()
