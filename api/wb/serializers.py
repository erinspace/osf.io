from django.db import IntegrityError

from api.base.serializers import (IDField,
                                  TypeField,)

from api.files.serializers import FileSerializer
from rest_framework import serializers as ser
from rest_framework import exceptions
from website.files import exceptions as file_exceptions


class WaterbutlerSerializer(ser.Serializer):
    source = ser.CharField(write_only=True)
    destination = ser.DictField(write_only=True, child=ser.CharField())

    id = IDField(source='_id', read_only=True)
    kind = ser.CharField(read_only=True)
    name = ser.CharField(read_only=True, help_text='Display name used in the general user interface')
    created = ser.CharField(read_only=True)
    modified = ser.CharField(read_only=True)
    path = ser.CharField(read_only=True)
    checkout = ser.SerializerMethodField(read_only=True)
    version = ser.IntegerField(help_text='Latest file version', read_only=True, source='current_version_number')
    downloads = ser.SerializerMethodField()

    sha256 = ser.SerializerMethodField()
    md5 = ser.SerializerMethodField()
    size = ser.SerializerMethodField()

    def get_checkout(self, obj):
        return obj.checkout._id if obj.checkout else None

    def get_downloads(self, obj):
        return obj.get_download_count()

    def get_sha256(self, obj):
        return obj.versions.first().metadata.get('sha256', None)

    def get_md5(self, obj):
        return obj.versions.first().metadata.get('md5', None)

    def get_size(self, obj):
        if obj.versions.exists():
            self.size = obj.versions.first().size
            return self.size
        return None

    def create(self, validated_data):
        source = validated_data.pop('source')
        destination = validated_data.pop('destination')
        action = validated_data.pop('action', '')
        name = validated_data.pop('name')

        try:
            # Current actions are only move and copy
            import pdb; pdb.set_trace()
            return source.copy_under(destination, name) if action == 'copy' else source.move_under(destination, name)
        except IntegrityError:
            raise exceptions.ValidationError('File already exists with this name.')
        except file_exceptions.FileNodeCheckedOutError:
            raise exceptions.ValidationError('Cannot move file as it is checked out.')
        except file_exceptions.FileNodeIsPrimaryFile:
            raise exceptions.ValidationError('Cannot move file as it is the primary file of preprint.')

    class Meta:
        type_ = 'file_metadata'
