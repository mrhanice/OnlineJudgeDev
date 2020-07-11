from copy import deepcopy
from unittest import mock

from problem.models import Problem, ProblemTag
from utils.api.tests import APITestCase
from .models import Submission

DEFAULT_PROBLEM_DATA = {"_id": "1001", "title": "test", "description": "<p>test</p>", "input_description": "test",
                        "output_description": "test", "time_limit": 1000, "memory_limit": 256, "difficulty": "Low",
                        "visible": True, "tags": ["test"], "languages": ["C", "C++", "Java", "Python2"], "template": {},
                        "samples": [{"input": "test", "output": "test"}], "spj": False, "spj_language": "C",
                        "spj_code": "", "test_case_id": "499b26290cc7994e0b497212e842ea85",
                        "test_case_score": [{"output_name": "1.out", "input_name": "1.in", "output_size": 0,
                                             "stripped_output_md5": "d41d8cd98f00b204e9800998ecf8427e",
                                             "input_size": 0, "score": 0}],
                        "rule_type": "ACM", "hint": "<p>test</p>", "source": "test"}

src = '''package com.hadoop;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.IntWritable;
import org.apache.hadoop.io.LongWritable;
import org.apache.hadoop.io.Text;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.mapreduce.Mapper;
import org.apache.hadoop.mapreduce.Reducer;
import org.apache.hadoop.mapreduce.lib.input.FileInputFormat;
import org.apache.hadoop.mapreduce.lib.output.FileOutputFormat;
import org.apache.log4j.Logger;

import java.io.IOException;

class WcMapper extends Mapper<LongWritable, Text,Text, IntWritable> {
    private Text word = new Text();
    private IntWritable one = new IntWritable(1);

    @Override
    protected void map(LongWritable key, Text value, Context context) throws IOException, InterruptedException {
        //拿到这一行数据
        String line = value.toString();
        String[] words = line.split(" ");
        for(String word: words) {
            this.word.set(word);
            context.write(this.word,one);
        }
    }
}

class WcReducer extends Reducer<Text, IntWritable,Text, IntWritable> {
    private IntWritable totol = new IntWritable();

    @Override
    protected void reduce(Text key, Iterable<IntWritable> values, Context context) throws IOException, InterruptedException {
        int sum = 0;
        for(IntWritable value: values) {
            sum += value.get();
        }
        totol.set(sum);
        context.write(key,totol);
    }
}

public class Main {

    public static void main(String[] args) throws IOException, ClassNotFoundException, InterruptedException {

        Configuration conf =new Configuration();
        //String[] otherArgs =new GenericOptionsParser(conf, args).getRemainingArgs();

        //(1) 获取一个job实例
        Job job = Job.getInstance(conf);
        //(2) 设置我们的类路径(ClassPath)
        job.setJarByClass(Main.class);
        //(3) 设置Mapper和Reducer
        job.setMapperClass(WcMapper.class);
        job.setReducerClass(WcReducer.class);
        //(4) 设置Mapper和Reducer输出类型
        job.setMapOutputKeyClass(Text.class);
        job.setMapOutputValueClass(IntWritable.class);

        job.setNumReduceTasks(3);
        job.setOutputKeyClass(Text.class);
        job.setMapOutputValueClass(IntWritable.class);

        //(5)设置输入输出数据
        FileInputFormat.setInputPaths(job,new Path(args[0]));
        FileOutputFormat.setOutputPath(job,new Path(args[1]));

        //int numa = 10;
        //int nmmb = 10/0;

        //(6) 提交我们的job
        boolean b = job.waitForCompletion(true);
        System.exit(b ? 0 : 1);
    }
}'''

DEFAULT_SUBMISSION_DATA = {
    "problem_id": "1001",
    "user_id": 1,
    "username": "test",
    "code": src,
    "result": -2,
    "info": {},
    "language": "hadoop",
    "statistic_info": {}
}


# todo contest submission


class SubmissionPrepare(APITestCase):
    def _create_problem_and_submission(self):
        user = self.create_admin("test", "test123", login=False) #创建一个admin用户
        problem_data = deepcopy(DEFAULT_PROBLEM_DATA) #拷贝题目数据
        tags = problem_data.pop("tags")
        problem_data["created_by"] = user
        self.problem = Problem.objects.create(**problem_data) #创建一个这样的题目
        for tag in tags:
            tag = ProblemTag.objects.create(name=tag)
            self.problem.tags.add(tag)
        self.problem.save()
        self.submission_data = deepcopy(DEFAULT_SUBMISSION_DATA) #拷贝提交数据
        self.submission_data["problem_id"] = self.problem.id
        self.submission = Submission.objects.create(**self.submission_data) #创建一个submission


class SubmissionListTest(SubmissionPrepare):
    def setUp(self):
        self._create_problem_and_submission()
        self.create_user("123", "345")
        self.url = self.reverse("submission_list_api")

    def test_get_submission_list(self):
        resp = self.client.get(self.url, data={"limit": "10"})
        self.assertSuccess(resp)


@mock.patch("submission.views.oj.judge_task.send")
class SubmissionAPITest(SubmissionPrepare):
    def setUp(self):
        self._create_problem_and_submission()
        self.user = self.create_user("123", "test123")
        self.url = self.reverse("submission_api")

    def test_create_submission(self, judge_task):
        # print('submission data = ',self.submission_data)
        resp = self.client.post(self.url, self.submission_data)
        self.assertSuccess(resp)
        # judge_task.assert_called()

    def test_create_submission_with_wrong_language(self, judge_task):
        self.submission_data.update({"language": "Python3"})
        resp = self.client.post(self.url, self.submission_data)
        self.assertFailed(resp)
        self.assertDictEqual(resp.data, {"error": "error",
                                         "data": "Python3 is now allowed in the problem"})
        judge_task.assert_not_called()
