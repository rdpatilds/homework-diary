/** Enough to say whose submission this is. */
export type StudentRef = {
  className: string;
  section: string;
  rollNo: string;
};

export type Student = StudentRef & {
  studentName: string;
};

/** Mirrors the server's discriminated union. A done assignment always carries
 * its time and an open one never does. */
export type AssignmentStatus =
  | { state: "open" }
  | { state: "missed" }
  | { state: "done"; submittedAt: string };

export type Assignment = {
  id: number;
  title: string;
  subject: string;
  details: string;
  className: string;
  section: string;
  dueAt: string;
  assignedBy: string;
  status: AssignmentStatus;
};

export type StudentDiary = {
  student: Student;
  asOf: string;
  assignments: Assignment[];
};

/** The teacher surfaces have no student, so no status. */
export type Homework = Omit<Assignment, "status">;

export type NewHomework = {
  title: string;
  subject: string;
  details: string;
  className: string;
  section: string;
  assignedBy: string;
  dueAt: string;
};
