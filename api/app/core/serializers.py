from rest_framework import serializers
from .models import Job, File, AnalysisJob, AnalysisFile


class FileSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="files-detail", source="id"
    )

    class Meta:
        model = File
        fields = ("id", "url", "file_name", "file_type", "md5sum")
        read_only_fields = ("md5sum",)


class JobSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="jobs-detail", source="id"
    )
    parent_url = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="jobs-detail", source="parent"
    )
    children_url = serializers.HyperlinkedRelatedField(
        many=True, read_only=True, view_name="jobs-detail", source="children"
    )
    job_files = FileSerializer(many=True, read_only=True)

    class Meta:
        model = Job
        fields = (
            "id",
            "url",
            "created_at",
            "status",
            "action",
            "template",
            "data",
            "ignore",
            "files",
            "submission",
            "raw_submission",
            "result",
            "raw_result",
            "links",
            "job_files",
            "parent",
            "parent_url",
            "children",
            "children_url",
        )
        read_only_fields = (
            "id",
            "created_at",
            "status",
            "action",
            "submission",
            "raw_submission",
            "result",
            "raw_result",
            "links",
            "job_files",
            "parent",
            "children",
        )


class AnalysisFileSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="analysisfiles-detail", source="id"
    )
    job_url = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="analysisjobs-detail", source="job"
    )

    class Meta:
        model = AnalysisFile
        fields = ("id", "url", "job", "job_url", "file_name", "file_type", "md5sum")
        read_only_fields = ("md5sum",)


class AnalysisJobSerializer(serializers.ModelSerializer):
    url = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="analysisjobs-detail", source="id"
    )
    job_url = serializers.HyperlinkedRelatedField(
        read_only=True, view_name="jobs-detail", source="job"
    )
    analysisjob_files = AnalysisFileSerializer(many=True, read_only=True)

    class Meta:
        model = AnalysisJob
        fields = (
            "id",
            "url",
            "job",
            "job_url",
            "created_at",
            "status",
            "template",
            "data",
            "manifest",
            "result",
            "raw_result",
            "analysisjob_files",
        )
        read_only_fields = (
            "id",
            "job_url",
            "created_at",
            "status",
            "manifest",
            "result",
            "raw_result",
            "analysisjob_files",
        )
