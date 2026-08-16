export type Student = {
  studentName: string;
  rollNo: string;
  className: string;
  section: string;
};

export type Homework = {
  id: number;
  title: string;
  subject: string;
  details: string;
  className: string;
  section: string;
  dueAt: string;
  assignedBy: string;
};

export type PendingHomework = {
  student: Student;
  asOf: string;
  items: Homework[];
};

export type NewHomework = {
  title: string;
  subject: string;
  details: string;
  className: string;
  section: string;
  assignedBy: string;
  dueAt: string;
};
