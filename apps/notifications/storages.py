"""Backends de armazenamento para mídia e estáticos usando Bucketeer/S3."""

from storages.backends.s3boto3 import S3Boto3Storage


class PrivateMediaStorage(S3Boto3Storage):
    """Storage privado para uploads e mídias sensíveis."""

    location = 'media'
    default_acl = None
    file_overwrite = False
    querystring_auth = True


class PublicStaticStorage(S3Boto3Storage):
    """Storage público para arquivos estáticos versionáveis."""

    location = 'static'
    default_acl = None
    file_overwrite = True
    querystring_auth = False
